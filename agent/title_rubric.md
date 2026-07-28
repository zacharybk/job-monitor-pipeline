# Title-first classifier rubric (Zach)

The cheap first-pass filter. Classify each job TITLE (+ company, location) as YES / MAYBE / NO
before any expensive JD fetch or scoring. Aligned with Zach 2026-07-28.

## YES — auto deep-dive and package
Customer Experience, Customer Success, Support, Member/Client Experience, Operations,
Business Operations, Strategy & Operations — at ANY level (IC, Manager, Senior Manager,
Director, Head, VP). Leadership OR individual contributor. Must be remote and US-eligible.
Examples: Head of CX, Customer Success Manager, Support Enablement Lead, Business Operations
Manager, Strategy & Ops Manager, Director of Member Experience, Clinical Success.

## MAYBE — send to the Review queue for Zach to tap Apply / No
Genuinely ambiguous roles where the title alone can't decide; Zach wants to eyeball them.
- **Revenue Operations (RevOps)** — depends on the role; some are real ops, some are sales-ops.
- **Product Manager / Senior PM** — he'd look, though it's usually a no.
- Ops-adjacent titles that could go either way (e.g. "Growth Strategy", a bare "Operations"
  role with no domain signal, GTM/BizOps hybrids).

## NO — drop before any further work
- Engineering of any kind, INCLUDING title-laundered ones: Software/Backend/Data/AI/Platform
  Engineer, Solutions Architect, Implementation Engineer, Forward Deployed Engineer, and
  "Customer Success Engineer" / "Product Support Engineer" (these are technical IC, not CX).
- Quota-carrying Sales, AE, RVP/VP Sales, Channel/Alliances, Partnerships/BD.
- Marketing (incl. partner/brand/growth marketing), Finance/Accounting, Recruiting/HR/Talent,
  Legal/Counsel, Design.
- **Workplace Operations / Workplace Experience** (office/facilities/employee experience, not customer).
- Executive Assistant, and non-professional/hourly roles.

## Flow
YES → agent packages it (pick + cover letter + contacts + outreach).
MAYBE → agent writes a lightweight pick with `fit_verdict='maybe'` (NO package yet); it shows
in the dashboard **Review** tab. Zach taps **Apply** (agent packages it next run) or **No**
(skip + the reason tunes this rubric).
NO → mark skipped with reason (visible in the QA tab).
