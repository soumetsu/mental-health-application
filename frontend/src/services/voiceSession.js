// Browser speech adapters are injected so conversation behavior can be tested without a microphone.
export function createVoiceSession({ Recognition, synthesis, Utterance, send, onState, onTranscript, onError, language = 'en-US' }) {
  let generation = 0
  let recognition = null
  let utterance = null
  let mode = 'conversation'
  let phase = 'idle'
  let useLocalRecognition = false
  const notify = (value) => { phase = value; onState({ phase, mode }) }
  const recognitionErrors = {
    'not-allowed': 'Microphone access was not allowed. Check microphone permissions for this site.',
    'service-not-allowed': 'This browser did not allow its speech recognition service.',
    'audio-capture': 'The browser could not capture audio. Check that your microphone is connected and selected.',
    network: 'The browser could not reach its speech recognition service.',
    'no-speech': 'No speech was heard. Start again when you are ready.',
    'language-not-supported': 'The browser does not support speech recognition for this language.',
    aborted: 'The browser ended speech recognition before a turn could finish.',
  }

  function stop() {
    generation += 1
    const previous = recognition
    recognition = null
    if (previous) {
      previous.onstart = previous.onresult = previous.onerror = previous.onend = null
      previous.abort()
    }
    if (utterance) utterance.onend = utterance.onerror = null
    utterance = null
    synthesis?.cancel()
    notify('idle')
  }

  function fail(message) {
    stop()
    onError(message)
  }

  function listen() {
    const ticket = ++generation
    let finalText = ''
    const current = new Recognition()
    recognition = current
    if (useLocalRecognition) current.processLocally = true
    current.lang = language
    current.continuous = false
    current.interimResults = true
    notify('starting')
    current.onstart = () => { if (ticket === generation && recognition === current) notify('listening') }
    current.onresult = (event) => {
      if (ticket !== generation || recognition !== current) return
      const finals = []
      const all = []
      for (const result of Array.from(event.results)) {
        const text = result[0].transcript.trim()
        all.push(text)
        if (result.isFinal) finals.push(text)
      }
      finalText = finals.join(' ').trim()
      onTranscript(all.join(' ').trim())
      // Submit only after recognition has ended: no listening during AI playback.
    }
    current.onerror = async (event) => {
      if (ticket !== generation || recognition !== current) return
      const reason = event.error
      const canTryLocal = !useLocalRecognition && ['network', 'service-not-allowed'].includes(reason)
        && 'processLocally' in current && typeof Recognition.available === 'function'
      recognition = null
      current.onstart = current.onresult = current.onerror = current.onend = null
      current.abort()
      if (canTryLocal) {
        notify('starting')
        let availability
        try {
          availability = await Recognition.available({ langs: [language], processLocally: true })
        } catch {
          // Some browser hosts block the on-device speech capability.
        }
        if (ticket !== generation) return
        if (availability === 'available') {
          useLocalRecognition = true
          try { listen(); return } catch { /* Show the original service failure. */ }
        }
      }
      fail(recognitionErrors[reason] || 'The browser could not recognize speech. Try again or type your message.')
    }
    current.onend = async () => {
      if (ticket !== generation || recognition !== current) return
      recognition = null
      current.onstart = current.onresult = current.onerror = current.onend = null
      if (mode === 'dictation') { notify('idle'); return }
      if (!finalText) { fail('No complete speech was heard. Start again when you are ready.'); return }
      if (finalText.length > 1200) { fail('That message is too long. Edit the transcript to 1,200 characters or fewer before sending.'); return }
      notify('thinking')
      try {
        const reply = await send(finalText)
        if (ticket !== generation) return
        if (!reply) throw new Error('No reply was available. Please try again.')
        utterance = new Utterance(reply)
        utterance.lang = language
        utterance.rate = 0.95
        utterance.onend = () => {
          if (ticket !== generation) return
          utterance = null
          try { listen() } catch { fail('The microphone could not reopen. Start again or continue typing.') }
        }
        utterance.onerror = () => {
          if (ticket === generation) fail('Audio playback stopped. Your AI reply is available in the chat. Start again or continue typing.')
        }
        notify('speaking')
        synthesis.speak(utterance)
      } catch (error) {
        if (ticket === generation) fail(error.message || 'The AI reply could not be loaded. Please try again.')
      }
    }
    try { current.start() } catch { fail('Voice input could not start in this browser. You can continue by typing.') }
  }

  function start(nextMode = 'conversation') {
    stop()
    mode = nextMode
    useLocalRecognition = false
    if (!Recognition || (mode === 'conversation' && (!synthesis || !Utterance))) {
      fail('Voice sessions are unavailable in this browser. You can continue with text chat.')
      return
    }
    try { listen() } catch { fail('Voice input could not start in this browser. You can continue by typing.') }
  }

  return { start, stop }
}
