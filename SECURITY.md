# Security policy

This repository holds prose, small tools and reproduction code. It runs no
service and stores no user data, so "security" here means three specific
things.

## What to report, and how

**Use [private vulnerability reporting](https://github.com/ma7moudalysalem/research-notebook/security/advisories/new)**,
not a public issue, for:

1. **A leaked credential.** Anything that looks like a token, key or password
   in this repository or its history. Report it privately even if it looks
   expired or fake — deciding that is my job, not yours.
2. **A hijacked link.** A URL in a reading list or summary whose domain has
   changed hands and now serves something else. These rot silently and a
   reading list is exactly the kind of page people follow links from without
   thinking.
3. **A vulnerability in `tools/`.** Realistically: a path traversal or an
   injection in code that other people run over their own files.

For a **copyright concern**, use the email in
[COPYRIGHT.md](COPYRIGHT.md#reporting-a-copyright-concern) instead. It is not a
security issue and it should not sit in a security queue.

## What happens next

I acknowledge within 7 days. There is no bounty and no SLA beyond that — this
is one person's notebook, and pretending otherwise would be worse than saying
so.

A leaked credential gets rotated first and investigated second.

## What is not in scope

- Links that are merely dead. Those are caught by the weekly link check and are
  not a security matter.
- Disagreements with a summary. Open an issue with the `correction` template;
  that is the engagement this repository wants most.
