# Security policy

This repository holds prose and one small tool. It runs no service and stores
no user data, so "security" here means three specific things.

## What to report, and how

**Use [private vulnerability reporting](https://github.com/ma7moudalysalem/research-notebook/security/advisories/new)**,
not a public issue, for:

1. **A leaked credential.** Anything that looks like a token, key or password
   in this repository or its history. Report it privately even if it looks
   expired or fake - deciding that is my job, not yours.
2. **A hijacked link.** A URL in a summary or in `docs/` whose domain has
   changed hands and now serves something else. These rot silently, and the
   source links at the foot of a summary are exactly the kind of link people
   follow without thinking.
3. **A vulnerability in `tools/`.** Realistically: a path traversal or an
   injection in `check_copyright.py`, which other people may run over their
   own files.

The form above needs a GitHub account. If you do not have one, email
[ma7moudalysalem@gmail.com](mailto:ma7moudalysalem@gmail.com) with the same
detail instead. That is ordinary mail rather than an encrypted channel, and
that is the trade: it reaches everyone, and you should treat what you send
over it as no more private than any other email. Use the form when you can.

For a **copyright concern**, use the email in
[COPYRIGHT.md](COPYRIGHT.md#reporting-a-copyright-concern) instead. It is not a
security issue and it should not sit in a security queue.

## What happens next

I acknowledge within 7 days. There is no bounty and no SLA beyond that - this
is one person's notebook, and pretending otherwise would be worse than saying
so.

A leaked credential gets rotated first and investigated second.

## What is not in scope

- Links that are merely dead. The link check runs on pull requests and on
  pushes to `main`, and nothing runs it on a schedule, so a link that dies in
  a quiet month stays dead until the next change. That is the trade for having
  no scheduled job here: it is a correction to file, not a security matter.
- Disagreements with a summary. Open an issue with the `correction` template;
  that is the engagement this repository wants most.
