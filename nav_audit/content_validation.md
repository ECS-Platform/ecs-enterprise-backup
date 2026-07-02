# Content Validation

Every nav route maps to a registered handler that returns a TemplateResponse (or an intentional redirect for stage routes).

- Handlers found: 64/64
- Templates exist on disk for all statically-linked routes (template_health 100%).
- No MISSING_TEMPLATE; no broken Jinja includes detected in nav partials (tag-balance verified).

Note: deep render of undefined Jinja variables requires a running server; not executed (no fastapi/jinja2 in this env).