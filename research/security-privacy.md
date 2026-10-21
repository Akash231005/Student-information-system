# Security and Privacy

## Threats
- Student reads another student's grades or attendance.
- Student invokes faculty/admin endpoints.
- Brute-force login or automated registration.
- Search leaks private fields.
- Grade edits lack traceability.
- Secrets or tokens appear in logs.
- Crawler ingests unsafe content.

## Minimum controls
1. Password hashing with a maintained library.
2. Server-side role checks on sensitive routes.
3. Object-level authorization on every record lookup.
4. Least privilege for students, faculty and admins.
5. Input validation and bounded payload sizes.
6. Rate limits for login and expensive endpoints.
7. Audit records for sensitive changes.
8. Secrets in environment variables, not source control.
9. Synthetic records for demos and load tests.
10. Never log passwords, tokens or sensitive payloads.

## References
OWASP API Security: https://owasp.org/www-project-api-security/
NIST Privacy Framework: https://www.nist.gov/privacy-framework
US FERPA: https://studentprivacy.ed.gov/ferpa . Useful as a US privacy reference, not Indian legal advice.

## Acceptance tests
- Student A cannot read Student B's grades by changing an ID.
- Students cannot publish grades.
- Faculty edit only assigned courses.
- Search excludes confidential fields.
- Sensitive changes create audit entries.