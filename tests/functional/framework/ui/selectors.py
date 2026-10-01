"""UI locators DERIVED FROM THE REAL ECS TEMPLATES (no invented selectors).

ECS templates do not use ``data-testid``; the stable hooks that exist are element ids / names / form actions /
visible labels, collected here with the template they come from. Add new entries only after confirming them in a template.
"""

# modules/executive_overview/templates/login.html
LOGIN = {"form": 'form[action="/login"]', "role": 'form[action="/login"] select[name="role"]',
         "submit": 'form[action="/login"] button'}

# modules/shared/templates/partials/evidence_upload_modal.html
UPLOAD_MODAL = {
    "modal": "#ecsEvidenceUploadModal", "form": "#ecsEvidenceUploadForm", "framework": "#ecsUploadFramework",
    "application": "#ecsUploadApplication", "control": "#ecsUploadControl", "owner": "#ecsUploadOwner",
    "type": "#ecsUploadType", "cycle": "#ecsUploadCycle", "comments": "#ecsUploadComments", "file": "#ecsUploadFile",
    "submit": "#ecsEvidenceUploadSubmit", "error": "#ecsUploadError", "success": "#ecsUploadSuccess",
    "toast": "#ecsUploadToast", "toast_body": "#ecsUploadToastBody"}

# modules/operations/templates/mvp_bulk_upload.html
BULK_UPLOAD = {"form": "#ecsBulkUploadForm", "files": '#ecsBulkUploadForm input[name="files"]',
               "submit": "#ecsBulkUploadForm button", "dataset": "#ecsOperationsDataset"}

# modules/shared/templates/shared/drilldown_modal.html
DRILLDOWN = {"modal": "#ecsUniversalDrillModal", "title": "#ecsUniversalDrillTitle", "body": "#ecsUniversalDrillBody"}

# modules/shared/templates/partials/standard_filter_include.html
FILTERS = {"dataset": "#ecsStandardDataset"}

# modules/shared/templates/partials/enterprise_widgets.html
NOTIFICATIONS = {"feed_item": ".notification-item", "activity": ".enterprise-feed"}

# Generic accessible fallbacks used when a page has no id-based hook
GENERIC = {"table": "table", "table_rows": "table tbody tr", "alert": '[role="alert"], .alert'}
