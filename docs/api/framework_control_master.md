# Framework Control Master — API Reference (Phase 1)

**Service:** `FrameworkControlMasterService` via `get_framework_control_master_service()`  
**Repository:** `FileFrameworkControlRepository` (`source_type: file`)  
**Catalogue:** `config/framework_control_master/`

---

## HTML routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/mvp/framework-control-master` | Framework Control Master browser (policies, controls, procedures, evidence tabs) |
| GET | `/mvp/evidence-dashboard` | Evidence Dashboard; use `tab=framework_progress` for FCM progress chart |

### Query parameters (HTML)

| Parameter | Applies to | Description |
|-----------|------------|-------------|
| `role` | Both | Demo persona (`owner`, `compliance_head`, `cio`, …) |
| `user` | Both | Display user label |
| `framework_id` | FCM page, Evidence Dashboard | Selected framework filter |
| `q` | FCM page | Control search query |
| `tab` | Evidence Dashboard | `overview`, `framework_progress`, `collection`, `health`, `approval` |
| `application` | Evidence Dashboard | Selected application for Framework Progress |

**Example — Framework Progress tab:**

```
/mvp/evidence-dashboard?role=owner&user=AppOwner&tab=framework_progress&application=Net%20Banking
```

---

## JSON — Framework Control Master

### List frameworks

```
GET /api/framework-control-master/frameworks
```

**Response:**

```json
{
  "ok": true,
  "source_type": "file",
  "frameworks": [ { "id": "pci_dss", "display_name": "...", "control_count": 6, ... } ],
  "stats": { "framework_count": 10, "control_count": 61, ... }
}
```

### Framework detail

```
GET /api/framework-control-master/frameworks/{framework_id}
```

`framework_id` accepts aliases (`PCI DSS`, `C-SITE`, `OS Baseline`, …).

**Response:** `framework`, `policies`, `controls`, `stats`.

### Control detail

```
GET /api/framework-control-master/controls/{framework_id}/{control_id}
```

**Response:** `framework`, `control`, `linked_policies`.

### Search controls

```
GET /api/framework-control-master/search?q=&framework_id=&domain=
```

**Response:** `controls[]` with `framework_id`, `framework_name`, control fields.

---

## JSON — Evidence Dashboard integration

### Framework progress (stacked chart data)

```
GET /api/evidence-dashboard/fcm-progress?role=owner&application=&framework_id=
```

**Response fields:**

| Field | Description |
|-------|-------------|
| `applications` | Role-scoped application list |
| `selected_application` | Active application |
| `legend` | Colour/status legend (`closed`, `pending`, `blocked`, `not_started`, `not_applicable`) |
| `chart_rows[]` | Per-framework `segments` counts + `total` |
| `control_rows[]` | Flat control list with `status` |
| `totals` | `controls`, `frameworks` |

**Colour mapping:**

| Segment key | Colour |
|-------------|--------|
| `closed` | Green |
| `pending` | Orange |
| `blocked` | Red |
| `not_started`, `not_applicable` | Grey |

### Control drill-down

```
GET /api/evidence-dashboard/fcm-drill/{framework_id}/{control_id}?application=&role=
```

**Response:** `framework`, `policy`, `control`, `procedures`, `evidence_requirements[]` (each with `requirement`, `submitted_evidence`, `status`), `control_status`, `drill_path[]`.

**RBAC:** When `role=owner` and `application` is outside owner scope, returns `{"ok": false, "message": "... not in role scope."}` with HTTP 404.

---

## Control closure (API semantics)

`control_status` in drill responses:

- **`closed`** — all evidence requirements `accepted`  
- **`pending`** — partial / under review  
- **`blocked`** — rejected, expired, or missing mandatory evidence  
- **`not_started`** — no submissions  
- **`not_applicable`** — control not applicable to application  

---

## Phase 1 limitations

- No write/upload APIs on this surface (read-only catalogue + progress).  
- Evidence payloads come from in-memory enrollments and legacy analytics, not direct Postgres repository queries.  
- Replace catalogue backend by implementing `FrameworkControlRepository` without changing these route signatures.
