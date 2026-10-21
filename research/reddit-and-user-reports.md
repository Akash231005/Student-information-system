# Reddit and User Reports

These are self-reported anecdotes. They help create test scenarios, not estimate prevalence.

- Registration crashes: https://www.reddit.com/r/college/comments/dpmaft/ . Reports describe synchronized registration and server crashes. Test burst traffic and clear retry guidance.
- HTTP 503 at registration: https://www.reddit.com/r/DeAnza/comments/1vkoqkb/ . Test error visibility, form-state preservation and retry safety.
- Recurring outages: https://www.reddit.com/r/UCR/comments/1wasjf3/ . Measure recovery time, not only average latency.
- Waitlist confusion: https://www.reddit.com/r/UCF/comments/1tez86e/ . Explain reserved seats and eligibility blockers.
- Course availability confusion: https://www.reddit.com/r/UNC/comments/1urdx0y/ . Distinguish full courses from seats reserved for other groups.
- Registration and SSO trouble: https://www.reddit.com/r/NEU/comments/yuys2a/ . Monitor authentication separately from registration.
- Grade-entry mistake: https://www.reddit.com/r/college/comments/18ido3c/ . Validate marks and retain correction history.

Convert each anecdote into a reproducible test. Verify policy choices using official university documentation. Use synthetic data in the prototype.