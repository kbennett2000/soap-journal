# 1. First login

The login screen is the first thing you see when you open soap-journal:

![Login page with Log in and Register tabs, Username and Password fields, and a Log in button](../screenshots/install-login-page.png)

There are two tabs:

- **Log in** — for an existing account. Type your username and password,
  click **Log in**.
- **Register** — for creating a new account. Same fields, but it only
  works in two situations:
  1. The instance is brand new and has no users yet. The first person
     to register automatically becomes the administrator.
  2. The admin has turned on **open registration** in
     **Admin → Settings**, allowing anyone with the URL to sign up.

If you try to register and get a "Registration is closed" error, that's
the admin keeping things closed. Ask them to either create an account
for you or to enable open registration.

## Username and password rules

- **Username** — 3 to 32 characters. Letters, digits, underscore (`_`),
  or hyphen (`-`). Stored lowercase — `Alice`, `alice`, and `ALICE`
  are all the same account.
- **Password** — at least 8 characters. No other constraints. Pick
  something you can remember; there is no self-service password reset
  in v0.1, and only an admin can reset it for you.

## What "logged in" means

Once you log in, soap-journal sets a long-lived cookie in your browser
so it remembers you. The cookie:

- Lasts up to **30 days**, refreshing on each visit.
- Survives closing and re-opening your browser.
- Is tied to one browser on one device. Logging in on your phone does
  not log you in on your laptop, and vice versa.
- Is encrypted and signed with the server's secret key — nobody who
  intercepts your traffic can forge it.

## Logging out

Click the **Log out** button in the top right corner of any screen.

That tells the server to invalidate the cookie for this device. Next
time you visit, you'll see the login page again.

> **You don't need to log out at the end of every session.** Closing
> the tab or shutting down your computer leaves you logged in for next
> time. Use **Log out** when you're on a device you share with someone
> else, or when you want to switch accounts.

## Multiple users on one device

soap-journal is happy with this. Log out, then log back in as the other
user. Each user has their own private journal — nobody else can see
your entries.

If two people use the same device a lot, browser profiles (one for each
person) are the smoothest way to keep things separate; each profile has
its own cookie jar.

---

Next: [The dashboard →](02-the-dashboard.md)
