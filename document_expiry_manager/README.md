# Document & License Expiry Tracker (Odoo 17)

A universal compliance tool to track the expiry of **any document** (licenses,
passports, insurance policies, contracts, certifications, warranties, permits...)
attached to **any record** in your Odoo database (Contacts, Employees, Vehicles,
Equipment, Projects, or any custom model) — with automated multi-stage reminders.

## Dependencies

Only `base` and `mail`. No vertical module (HR, Fleet, etc.) is required, so it
installs cleanly on any Odoo 17 database.

## Installation

1. Copy the `document_expiry_manager` folder into your Odoo `addons` path.
2. Restart the Odoo server (or update the apps list).
3. Go to **Apps**, remove the "Apps" filter, search for
   "Document & License Expiry Tracker", and click **Install**.

## Usage

1. **Settings > General Settings > Document Expiry** — set global defaults
   (warning window, reminder schedule).
2. **Document Expiry > Configuration > Document Types** — review/extend the
   default document types (Passport, License, Insurance, Contract, ...).
3. **Document Expiry > Dashboard** — create a new tracked document:
   - Pick a **Document Type**.
   - Pick **Applies To** (the target model, e.g. `res.partner`) and the
     **Record ID** of the specific record.
   - Set the **Expiry Date**, warning window, and reminder schedule.
4. A daily scheduled action (**Settings > Technical > Automation > Scheduled
   Actions > "Document Expiry Tracker: Check & Notify"**) automatically:
   - Updates the document's status (Valid / Expiring Soon / Expired).
   - Posts a chatter message and schedules an activity for the responsible
     user at each configured reminder threshold.
5. Use the **Renew** button to open the renewal wizard, set a new expiry date,
   and log the renewal in the chatter history.

## Security

Two groups are provided:
- **Document Expiry / User** — create, read, and update tracked documents.
- **Document Expiry / Manager** — full access, including document type
  configuration and deletion.

Multi-company record rules are included.

## License

OPL-1 (Odoo Proprietary License), suitable for paid listing on the Odoo Apps
Store. Update `author`, `website`, `price`, and `currency` in
`__manifest__.py` before publishing.
