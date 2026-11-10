import test from 'node:test'
import assert from 'node:assert/strict'
import { createVoiceSession } from '../src/services/voiceSession.js'

function setup(overrides = {}) {
  const recognizers = [], spoken = [], sent = [], states = [], errors = [], transcripts = []
  class Recognition {
    constructor() { recognizers.push(this) }
    start() { this.onstart?.() }
    abort() { this.aborted = true }
  }
  class Utterance { constructor(text) { this.text = text } }
  const voice = createVoiceSession({
    Recognition,
    synthesis: { cancel() {}, speak: (item) => spoken.push(item) },
    Utterance,
    send: async (text) => { sent.push(text); return 'A mocked AI reply.' },
    onState: (state) => states.push(state),
    onTranscript: (text) => transcripts.push(text),
    onError: (error) => errors.push(error),
    ...overrides,
  })
  const result = (text, isFinal = true) => Object.assign([{ transcript: text }], { isFinal })
  const say = (text, isFinal = true) => recognizers.at(-1).onresult({ results: [result(text, isFinal)] })
  const end = () => recognizers.at(-1).onend()
  return { voice, recognizers, spoken, sent, states, errors, transcripts, say, end, result }
}

test('spoken turn goes to AI once; next listening starts only after playback ends', async () => {
  const h = setup()
  h.voice.start()
  h.say('Help me reflect on today.')
  assert.deepEqual(h.sent, [])
  const end = h.recognizers[0].onend
  await end()
  await end()
  assert.deepEqual(h.sent, ['Help me reflect on today.'])
  assert.equal(h.spoken[0].text, 'A mocked AI reply.')
  assert.equal(h.recognizers.length, 1)
  assert.equal(h.states.at(-1).phase, 'speaking')
  h.spoken[0].onend()
  assert.equal(h.recognizers.length, 2)
  assert.equal(h.states.at(-1).phase, 'listening')
})

test('interim speech is displayed but never submitted as a completed turn', async () => {
  const h = setup()
  h.voice.start()
  h.say('unfinished', false)
  await h.end()
  assert.deepEqual(h.sent, [])
  assert.equal(h.transcripts.at(-1), 'unfinished')
  assert.match(h.errors[0], /No complete speech/)
})

test('multiple final segments form one message; interim words are excluded', async () => {
  const h = setup()
  h.voice.start()
  h.recognizers[0].onresult({ results: [h.result('One sentence.'), h.result('Another sentence.'), h.result('unfinished', false)] })
  await h.end()
  assert.deepEqual(h.sent, ['One sentence. Another sentence.'])
})

test('Stop during AI request prevents playback and microphone restart', async () => {
  let resolveReply
  const h = setup({ send: () => new Promise((resolve) => { resolveReply = resolve }) })
  h.voice.start()
  h.say('A fictional message')
  const request = h.end()
  h.voice.stop()
  resolveReply('Late AI reply')
  await request
  assert.equal(h.spoken.length, 0)
  assert.equal(h.recognizers.length, 1)
  assert.equal(h.states.at(-1).phase, 'idle')
})

test('Stop invalidates queued speech and recognition callbacks', async () => {
  const h = setup()
  h.voice.start()
  const staleResult = h.recognizers[0].onresult
  h.say('Hello')
  await h.end()
  const staleEnd = h.spoken[0].onend
  h.voice.stop()
  staleEnd()
  staleResult({ results: [h.result('Must not send')] })
  assert.equal(h.recognizers.length, 1)
  assert.deepEqual(h.sent, ['Hello'])
  assert.equal(h.transcripts.at(-1), 'Hello')
})

test('permission denial ends session without a model call', () => {
  const h = setup()
  h.voice.start()
  h.recognizers[0].onerror({ error: 'not-allowed' })
  assert.match(h.errors[0], /Microphone access/)
  assert.equal(h.states.at(-1).phase, 'idle')
  assert.equal(h.sent.length, 0)
  assert.equal(h.recognizers[0].aborted, true)
})

test('model failure ends session with a recoverable error', async () => {
  const h = setup({ send: async () => { throw new Error('Mock provider unavailable') } })
  h.voice.start()
  h.say('Hello')
  await h.end()
  assert.equal(h.errors[0], 'Mock provider unavailable')
  assert.equal(h.spoken.length, 0)
  assert.equal(h.states.at(-1).phase, 'idle')
})

test('dictation fills draft without sending to the AI', async () => {
  const h = setup()
  h.voice.start('dictation')
  h.say('Draft for review')
  await h.end()
  assert.equal(h.transcripts.at(-1), 'Draft for review')
  assert.equal(h.sent.length, 0)
  assert.equal(h.states.at(-1).phase, 'idle')
})

test('unsupported browser and overlong transcript do not call the AI', async () => {
  const unsupported = setup({ Recognition: null })
  unsupported.voice.start()
  assert.match(unsupported.errors[0], /unavailable/)
  const h = setup()
  h.voice.start()
  h.say('a'.repeat(1201))
  await h.end()
  assert.equal(h.sent.length, 0)
  assert.match(h.errors[0], /too long/)
})

test('playback failure returns to text without restarting microphone', async () => {
  const h = setup()
  h.voice.start()
  h.say('Hello')
  await h.end()
  h.spoken[0].onerror()
  assert.equal(h.recognizers.length, 1)
  assert.match(h.errors[0], /playback stopped/)
  assert.equal(h.states.at(-1).phase, 'idle')
})

test('a failed speech service retries with an installed on-device language', async () => {
  const recognizers = []
  class Recognition {
    processLocally = false
    constructor() { recognizers.push(this) }
    start() { this.onstart() }
    abort() {}
    static async available(options) {
      assert.equal(options.processLocally, true)
      return 'available'
    }
  }
  const h = setup({ Recognition })
  h.voice.start()
  await recognizers[0].onerror({ error: 'network' })
  assert.equal(recognizers.length, 2)
  assert.equal(recognizers[1].processLocally, true)
  assert.equal(h.states.at(-1).phase, 'listening')
  assert.deepEqual(h.sent, [])
  assert.deepEqual(h.errors, [])
})

test('speech network and microphone capture errors produce distinct recovery messages', async () => {
  for (const [error, expected] of [['network', /speech recognition service/], ['audio-capture', /could not capture audio/]]) {
    const h = setup()
    h.voice.start()
    await h.recognizers[0].onerror({ error })
    assert.match(h.errors[0], expected)
    assert.equal(h.states.at(-1).phase, 'idle')
    assert.deepEqual(h.sent, [])
  }
})

test('a missing local speech pack ends the browser session without installing anything', async () => {
  const recognizers = []
  class Recognition {
    processLocally = false
    constructor() { recognizers.push(this) }
    start() { this.onstart() }
    abort() {}
    static async available() { return 'downloadable' }
    static async install() { assert.fail('The app does not install speech packs') }
  }
  const h = setup({ Recognition })
  h.voice.start()
  await recognizers[0].onerror({ error: 'network' })
  assert.match(h.errors[0], /speech recognition service/)
  assert.equal(h.states.at(-1).phase, 'idle')
  assert.equal(recognizers.length, 1)
  assert.deepEqual(h.sent, [])
})
