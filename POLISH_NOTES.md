# Interface polish and verification

## Changes

- Removed demo-account cards, automatic login shortcuts and frontend demo-credential requests.
- `/api/auth/demo` now returns an empty list, including in demo mode.
- Added a clean sign-in/account-creation layout and accessible show/hide password control.
- Added restrained Bangla tagline, wallet labels and navigation text, keeping primary actions clear in English.
- Applied the requested green/yellow palette, Inter + Hind Siliguri typography, SVG icons, refined cards and subtle watermark.
- Preserved reduced-motion preferences, keyboard focus indicators and responsive layouts.
- Removed customer presenter controls from the visible interface.
- Kept customer warnings understandable; customer screens no longer describe synthetic model scores as real-world fraud probabilities.
- Fixed icon class collisions that could stretch the navigation or login layout.
- Updated README/RUN instructions to match FastAPI + React.

## Verification

19 automated tests passed with the versions pinned in requirements.txt, including a regression check that the public demo endpoint exposes no credentials. Production frontend build completed.

Browser checks: normal login, no visible demo-account list, no demo-credential network requests, password visibility, sign-out, registration screen and bilingual navigation. Desktop and 390px mobile screens were checked; no JavaScript errors or horizontal overflow occurred. A final visual check followed the icon sizing correction.

The app still uses virtual funds and synthetic histories. These UI improvements do not establish live payment integration or production deployment readiness. Operator seed credentials remain in RUN.md for controlled local demonstrations and are not shown on the login page.
