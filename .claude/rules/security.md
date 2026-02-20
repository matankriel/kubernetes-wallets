# Security Rules

These rules apply globally to all code and configurations.

## OWASP Top 10 — Never Introduce

### 1. Injection (SQL, Command, LDAP)
- **Never** concatenate user input into SQL queries. Always use parameterized queries or an ORM.
- **Never** pass user input to `exec`, `eval`, `child_process.exec`, `os.system`, or `subprocess.run(shell=True)`.
- Validate and sanitize all input at system boundaries.

### 2. Broken Authentication
- Never store passwords in plaintext. Use bcrypt, argon2, or scrypt with appropriate cost factors.
- Never log passwords, tokens, or secrets — not even partially.
- Implement proper session invalidation on logout and password change.

### 3. Sensitive Data Exposure
- Never commit secrets, API keys, or credentials. Use environment variables.
- `.env` files are gitignored. Never add them to version control.
- Use `process.env.SECRET` patterns; never hardcode.
- Encrypt sensitive data at rest.

### 4. XML External Entities (XXE)
- Disable external entity processing in XML parsers.
- Prefer JSON over XML for data exchange.

### 5. Broken Access Control
- Default to deny. Explicitly allow only what is needed.
- Validate authorization on every request — don't rely on UI-level hiding.
- Use resource-based authorization (user owns the resource) not just role-based.

### 6. Security Misconfiguration
- Never enable debug endpoints in production.
- Remove default credentials and example configurations.
- Set security headers: `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`.

### 7. Cross-Site Scripting (XSS)
- Never render raw user input as HTML. Always escape/sanitize.
- Use template engines with auto-escaping enabled.
- Validate and sanitize rich text with an allowlist (e.g., DOMPurify).

### 8. Insecure Deserialization
- Never deserialize untrusted data into objects without validation.
- Use schema validation (Zod, Joi, Pydantic) on all incoming data.

### 9. Using Components with Known Vulnerabilities
- Run `npm audit` / `pip-audit` / `cargo audit` in CI.
- Keep dependencies updated. Pin versions but review updates regularly.
- Subscribe to security advisories for critical dependencies.

### 10. Insufficient Logging & Monitoring
- Log all authentication events (success and failure).
- Log all authorization failures.
- Never log sensitive data. Redact PII before logging.
- Include request IDs in all log lines for traceability.

## Code Review Security Checklist

Before merging any PR touching authentication, authorization, or data handling:

- [ ] No secrets in code or logs
- [ ] All inputs validated and sanitized
- [ ] Authorization checked server-side
- [ ] SQL uses parameterized queries
- [ ] No `eval` or dynamic code execution on user input
- [ ] Dependencies audited
- [ ] Error messages don't leak internal details to clients
