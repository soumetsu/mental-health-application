**Mental Health application that keeps track of events, positive or negative, and reacts/adapts to the user and their needs**

**Figma Wireframe:** https://www.figma.com/design/2RAqBd1XjJxep6rhTSN6yB/Untitled?node-id=0-1&t=s3wM32ATQuv2U47V-1
**GitHub Repository:** https://github.com/soumetsu/mental-health-application
**GitHub Commit:** https://github.com/soumetsu/mental-health-application/commit/fe33ca42f1b99afc5b48528c5118057b58ec002f

Goal is the same: to create a mental health application that keeps track of events, positive or negative, and reacts/adapts to the user.

The app consists of a login/profile creation screen,  a personalized dashboard, daily check-ins, an event calendar, grounding and breathing exercises, exercise history, and a supportive chatbot.

Breathing exercises: Used for grounding, follows the R&D research we've done. Is optional, and can be done at any time.


I've developed the front-end (VUE), and the back-end (FastAPI, SQLite). The chatbot feature uses an API key from Gemini (free usage at first, but had to add minimal credits for it to work). 


Some limitations are the chatbot; it is personalized and has a starting prompt, and will read the user's information, such as events recorded, exercises done, and more. The chat's main functionality though, is only to answer the user's request, and the chatbot provides support/information, such as recent events or exercises. I plan to have the AI be used in a slighly more active manner, where it can at least suggest more actions/have a more specific use case, such as being used for reflection only.

I plan to improve the overall front-end design, and add much more features than the exercises based off the reasearch. I plan to add more to the personalization than just changing the overall theme and suggestions. I also plan on adding more features that could use APIs or any external tools, such as calendars.
