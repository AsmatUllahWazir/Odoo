# Vendor Bill Dispatch - Multi-Company OCR Automation

## Overview

This Odoo 19 Enterprise module provides a complete solution for centralizing vendor bill processing across multiple companies with automatic OCR, intelligent dispatch, and multi-level validation workflows.

**Similar to:** Zendoc, Basware, Coupa Invoice Automation

## 🎯 Key Features

### 📄 OCR Processing
- **Automatic OCR** on document upload using Odoo Document Digitization (IAP)
- Extract vendor information, amounts, dates, taxes automatically
- Configurable confidence thresholds
- Manual fallback when OCR fails

### 🎯 Smart Dispatch
- **Rule-based routing** to target companies
- **9 Rule Types:**
  - Vendor name pattern matching (wildcards supported)
  - Vendor VAT/Tax ID patterns
  - Vendor country
  - IBAN patterns
  - Currency matching
  - Amount ranges
  - OCR keyword detection
  - Specific partner matching
  - Advanced domain filters
- Unlimited configurable rules with priority system
- Fallback options for unmatched bills

### ✅ Multi-Level Validation Workflow
- **Business Validation**: Content verification by business managers
- **Finance Validation**: CFO approval for high-value invoices (configurable threshold)
- **Accounting Validation**: Final manual posting by accountants
- Rejection workflow with mandatory comments
- Complete audit trail

### 🏢 Multi-Company Support
- Centralized HUB company for OCR processing
- Strict company separation and security
- Multi-company record rules
- Company-specific journals and accounts

### 📊 Analytics & KPIs
- Auto-routing success rate
- OCR performance metrics
- Average processing times
- Rejection analytics
- Dashboard with graphs and pivot tables

---

## 📋 Table of Contents

1. [Installation](#installation)
2. [Configuration](#configuration)
3. [Usage](#usage)
4. [User Roles](#user-roles)
5. [Workflows](#workflows)
6. [Advanced Features](#advanced-features)
7. [Troubleshooting](#troubleshooting)
8. [Best Practices](#best-practices)

---

## 🚀 Installation

### Prerequisites
- Odoo 19 Enterprise
- Active IAP credits for Document Digitization
- Multi-company environment configured
- Purchase journals set up per company

### Installation Steps

1. **Copy module to Odoo addons directory:**
```bash
   cp -r vendor_bill_dispatch /path/to/odoo/addons/
```

2. **Restart Odoo:**
```bash
   sudo systemctl restart odoo
```

3. **Update apps list:**
   - Go to: Apps > Update Apps List

4. **Install the module:**
   - Search for "Vendor Bill Dispatch"
   - Click Install

5. **Verify installation:**
   - New menu "Bill Dispatch" should appear in main menu
   - Configuration wizard will create HUB company automatically

---

## ⚙️ Configuration

### 1. Basic Configuration

Navigate to: **Bill Dispatch > Configuration > Dispatch Configuration**

#### HUB Company Setup
- Select or verify the HUB company (auto-created during installation)
- This company will be the initial recipient of all vendor bills

#### OCR Settings
```
Provider: Odoo Document Digitization (IAP)
Auto OCR on Upload: ✓ Enabled
Confidence Threshold: 70%
```

#### Validation Workflow
```
Enable Business Validation: ✓ Enabled
Enable Finance Validation: ✓ Enabled
Finance Threshold: €5,000 (adjust based on your needs)
```

#### Notifications
```
Notify on Dispatch: ✓ Enabled
Notify Business Validator: ✓ Enabled
Notify Finance Validator: ✓ Enabled
```

---

### 2. Create Dispatch Rules

Navigate to: **Bill Dispatch > Configuration > Dispatch Rules**

#### Example Rules:

**Rule 1: Belgian Vendors (by VAT)**
```
Name: Belgium Company Vendors
Type: Vendor VAT
Pattern: BE*
Target Company: Company A (Belgium)
Priority: 10
```

**Rule 2: French IBAN**
```
Name: French Bank Accounts
Type: IBAN
Pattern: FR*
Target Company: Company B (France)
Priority: 20
```

**Rule 3: High-Value EUR Invoices**
```
Name: Large EUR Invoices
Type: Amount Range
Min Amount: 10,000 EUR
Currency: EUR
Target Company: Company A (Belgium HQ)
Priority: 30
```

**Rule 4: Keyword Detection**
```
Name: Paris Office Keywords
Type: OCR Keywords
Keywords (one per line):
  Paris
  French Office
  Bureau Paris
Match Type: Any
Target Company: Company B (France)
Priority: 40
```

**Rule 5: Specific Vendors**
```
Name: Dell Computers
Type: Vendor Name
Pattern: Dell*
Target Company: Company A
Priority: 15
```

---

### 3. Configure User Roles

Navigate to: **Settings > Users & Companies > Users**

For each user:
1. Edit user
2. Go to "Access Rights" tab
3. Under "Vendor Bill Dispatch" section, select role:

| User | Role | Permissions |
|------|------|-------------|
| Sarah (DMS) | DMS User | Upload bills, view OCR |
| John (Manager) | Business Validator | Approve from business side |
| Marie (Accountant) | Business Validator | Approve and post |
| Pierre (CFO) | Finance Validator | Approve high-value bills |
| IT Admin | Dispatch Administrator | Full system access |

---

### 4. Email Reception (Optional)

To receive bills via email:

1. **Configure in module:**
```
   Bill Dispatch > Configuration > Settings
   Enable Email Reception: ✓
   Email Alias: vendor.bills
```

2. **Setup incoming mail server:**
```
   Settings > Technical > Email > Incoming Mail Servers
   Add your IMAP/POP3 configuration
```

3. **Test:**
```
   Send test PDF to: vendor.bills@yourdomain.com
   Verify it appears in Bill Dispatch > Vendor Bills > OCR Draft
```

---

## 👥 User Roles

### 1. DMS User
**Who:** All employees who upload invoices

**Can:**
- Upload vendor bills (manually or via email)
- View OCR results
- See dispatch status

**Cannot:**
- Approve or validate invoices
- Configure rules
- Change companies

### 2. Business Validator
**Who:** Department managers, purchasing managers

**Can:**
- All DMS User permissions
- Review invoice content
- Approve invoices from business perspective
- Reject invoices with reason
- View validation history

**Cannot:**
- Approve high-value invoices requiring finance approval
- Configure system

### 3. Finance / CFO Validator
**Who:** CFO, Finance Director, Finance team

**Can:**
- All Business Validator permissions
- Approve high-value invoices (above threshold)
- View all financial analytics
- Access dashboard

**Cannot:**
- Configure rules (but can view them)

### 4. Dispatch Manager
**Who:** Power users, operations managers

**Can:**
- All Finance Validator permissions
- Create and modify dispatch rules
- View complete statistics
- Manage workflows
- Configure notifications

**Cannot:**
- Modify system configuration settings

### 5. Dispatch Administrator
**Who:** IT team, implementation consultants

**Can:**
- Everything (full system access)
- Modify system configuration
- Change HUB company
- Modify OCR settings
- Override security restrictions (use carefully!)

---

## 📝 Usage Workflows

### Standard Workflow
```
1. UPLOAD/EMAIL
   ↓
2. AUTO OCR (HUB Company)
   ↓
3. AUTO DISPATCH (Rule Matching)
   ↓
4. SUBMIT FOR APPROVAL
   ↓
5. BUSINESS VALIDATION
   ↓
6. FINANCE VALIDATION (if high-value)
   ↓
7. ACCOUNTING POSTING (Manual)
```

### Detailed Process

#### Step 1: Upload Vendor Bill

**Method A: Manual Upload**
```
1. Go to: Bill Dispatch > Vendor Bills > OCR Draft
2. Click "Create"
3. Upload PDF file
4. System automatically triggers OCR
```

**Method B: Email Reception**
```
1. Send invoice PDF to: vendor.bills@yourdomain.com
2. System automatically:
   - Creates invoice in HUB company
   - Triggers OCR processing
   - Extracts data
```

#### Step 2: OCR Processing (Automatic)

System extracts:
- Vendor name, VAT, address
- Invoice number, date, due date
- Amounts, taxes, currency
- Full text for keyword matching

**What to check:**
- OCR Confidence percentage (should be >70%)
- Vendor correctly identified
- Amount correct
- Date correct

**If OCR fails:**
- Manually correct extracted data
- Or enter data manually
- System will still dispatch based on manual data

#### Step 3: Auto Dispatch (Automatic)

**What happens:**
```
1. System evaluates ALL active rules in priority order
2. First matching rule found
3. Invoice moved to target company
4. Journal updated to company's purchase journal
5. Accounts recalculated for company
6. State changes to "Routed"
```

**If no rule matches:**
- Manual dispatch wizard appears
- Select target company manually
- Add notes explaining decision
- System dispatches invoice

#### Step 4: Submit for Approval

**Who does this:** Usually DMS User or automatic
```
1. Open invoice
2. Click "Submit for Approval"
3. Invoice state changes to "To Approve"
4. Business validators receive notification
```

#### Step 5: Business Validation

**Who does this:** Business Manager

**What to check:**
- Is this really our invoice?
- Did we order this?
- Is the amount correct?
- Is the vendor correct?
- Does it match purchase order?

**Options:**
```
✓ Approve: Click "Business Approve"
  → Moves to next step
  → If high-value, goes to Finance
  → If not high-value, ready for posting

✗ Reject: Click "Reject"
  → Must provide reason (min 10 characters)
  → Invoice marked as rejected
  → Submitter notified
```

#### Step 6: Finance Validation (Conditional)

**Only if:** Amount ≥ Finance Threshold (e.g., €5,000)

**Who does this:** CFO / Finance Director

**What to check:**
- Budget availability
- Cash flow impact
- Approval authority
- Contract compliance

**Action:**
```
1. Open invoice
2. Review amount and details
3. Click "Finance Approve"
4. Invoice ready for posting
```

#### Step 7: Accounting Posting (Manual)

**Who does this:** Accountant

**Final checks:**
- All approvals completed
- Company correct
- Journal entries correct
- Taxes correct

**Action:**
```
1. Open invoice
2. Final review
3. Click "Post" button
4. Invoice recorded in accounting
```

---

### Rejection Workflow

#### When to Reject:
- Wrong company
- Incorrect amount
- Not our invoice
- Duplicate invoice
- Missing documentation
- Contract issue

#### How to Reject:
```
1. Open invoice
2. Click "Reject" button
3. Enter detailed reason (minimum 10 characters)
4. Optionally notify submitter
5. Click "Reject Invoice"
```

**What happens:**
- Invoice state changes to "Rejected"
- Rejection logged in validation history
- Submitter receives notification (if enabled)
- Invoice cannot be posted
- Can be corrected and resubmitted

#### After Rejection:
```
Option 1: Fix and resubmit
  - Correct the issue
  - Reset workflow
  - Resubmit for approval

Option 2: Cancel
  - Cancel the invoice
  - Archive it
```

---

### Bulk Operations

For processing multiple invoices at once:

#### Bulk Approval
```
1. Go to: Bill Dispatch > Vendor Bills > To Approve
2. Select multiple invoices (checkboxes)
3. Actions menu > "Bulk Approve"
4. Select approval type:
   - Business Approval
   - Finance Approval
5. Optional: Add approval notes
6. Click "Approve All"
```

**System will:**
- Approve all eligible invoices
- Skip invoices not in correct state
- Report success/failure count
- Show error details for failed items

---

## 🔧 Advanced Features

### 1. Manual Dispatch

When no rule matches:
```
1. Manual dispatch wizard appears
2. Shows suggested company (if rule matched with low confidence)
3. Select target company from dropdown
4. Add notes explaining your decision
5. Click "Dispatch"
```

**Good practice:**
- Always add notes for manual dispatch
- Document why you chose this company
- This helps create better rules later

### 2. Rule Testing

Before activating a rule, test it:
```
1. Open the dispatch rule
2. Click "Test Rule" button
3. System checks last 50 invoices
4. Shows how many would have matched
5. Review results
6. Adjust criteria if needed
7. Save and activate
```

### 3. Validation History

Every invoice maintains complete audit trail:
```
To view:
1. Open invoice
2. Go to "Dispatch Info" tab
3. See "Validation History" section
```

**Tracks:**
- Every state change
- User who made change
- Timestamp (exact date/time)
- Before/after company values
- Approval/rejection details
- IP addresses (for security audit)

### 4. OCR Reprocessing

If OCR failed or produced poor results:
```
1. Open invoice
2. Go to "Dispatch Info" tab
3. Click on OCR Result record
4. Click "Reprocess OCR"
5. System runs OCR again
```

### 5. Company Change Lock

For accounting compliance:

**Default behavior:**
- Company CANNOT be changed after business validation
- This prevents accounting fraud
- Configurable in settings

**To allow changes (not recommended):**
```
Bill Dispatch > Configuration > Settings
Advanced Settings tab:
  Lock Company After Validation: Uncheck
```

---

## 📊 Dashboards & Reporting

### KPI Dashboard

Navigate to: **Bill Dispatch > Reporting > Dispatch Dashboard**

#### Available Metrics:

**Volume Metrics:**
- Total bills processed
- Auto-routed bills
- Manually routed bills
- Rejected bills

**Performance Metrics:**
- Auto-routing percentage (target: >85%)
- OCR success rate
- Average OCR confidence
- Processing time (hours)

**Approval Metrics:**
- Business approval time
- Finance approval time
- Rejection rate
- Invoices awaiting approval

#### Views:

**Graph View:** Trends over time
```
- Line chart showing auto-routing %
- Bar chart for volume
- Filter by date range
- Group by month/quarter
```

**Pivot View:** Multi-dimensional analysis
```
- Rows: Date periods
- Columns: Companies
- Measures: Any KPI metric
- Drill down capabilities
```

**Tree View:** Detailed data
```
- Export to Excel
- Filter and sort
- Custom analysis
```

---

### Validation History Report

Navigate to: **Bill Dispatch > Reporting > Validation History**

**Use cases:**
- Audit who approved what and when
- Find patterns in rejections
- Analyze processing times
- Compliance reporting

**Filters available:**
- Date range
- User
- Company
- Action type
- Invoice

---

## 🔍 Troubleshooting

### Problem 1: OCR Not Working

**Symptoms:**
- "OCR Error" message
- No data extracted
- Low confidence scores

**Solutions:**

1. **Check IAP Credits:**
```
   Settings > Technical > IAP > Accounts
   Verify you have credits for "Document Digitization"
```

2. **Check document quality:**
   - Must be PDF format
   - Clear, not blurry
   - Properly oriented (not upside down)
   - Good resolution (300 DPI recommended)

3. **Check OCR provider:**
```
   Bill Dispatch > Configuration > Settings
   OCR Provider: Should be "Odoo IAP"
```

4. **Test with different document:**
   - Try a different invoice
   - If that works, original document is the issue

5. **Manual entry:**
   - As fallback, enter data manually
   - System will still dispatch based on manual data

---

### Problem 2: Dispatch Rules Not Matching

**Symptoms:**
- All invoices require manual dispatch
- Rules not being triggered
- Wrong company selected

**Solutions:**

1. **Check rule is active:**
```
   Bill Dispatch > Configuration > Dispatch Rules
   Verify "Active" checkbox is checked
```

2. **Test the rule:**
```
   Open the rule
   Click "Test Rule" button
   See if it matches recent invoices
```

3. **Check rule criteria:**
```
   Vendor Name patterns:
   ✓ Correct: Dell*
   ✗ Wrong: dell (case matters for patterns)
   
   VAT patterns:
   ✓ Correct: BE*
   ✗ Wrong: BE123456789 (too specific)
```

4. **Check rule priority:**
```
   Lower priority number = evaluated first
   Rule priority 10 runs before priority 20
```

5. **Check vendor data:**
```
   Open vendor (partner)
   Verify:
   - VAT is filled in correctly
   - Country is set
   - Bank accounts have IBAN
```

6. **Check OCR extracted data:**
```
   If rule matches on vendor VAT
   But OCR didn't extract VAT
   Rule won't match!
   
   Solution: Improve OCR or add additional rules
```

---

### Problem 3: Permission Errors

**Symptoms:**
- User cannot approve invoice
- "You do not have permission" error
- Buttons not visible

**Solutions:**

1. **Check user role:**
```
   Settings > Users > Edit User
   Access Rights tab
   Vendor Bill Dispatch section:
   - Verify correct role assigned
```

2. **Check multi-company access:**
```
   Settings > Users > Edit User
   Allowed Companies tab:
   - User must have access to the invoice's company
```

3. **Check invoice state:**
```
   Business approval only available when state = "To Approve"
   Finance approval only available when state = "Approved" AND amount > threshold
```

4. **Refresh browser:**
```
   Sometimes permissions don't update immediately
   Press Ctrl+Shift+R to hard refresh
```

---

### Problem 4: Company Changes Not Allowed

**Symptoms:**
- Cannot change company field
- "Cannot change company after validation" error

**Why:**
- This is by design for accounting compliance
- Prevents fraud and mistakes

**Solutions:**

1. **If invoice not yet validated:**
```
   Reset to OCR Draft state
   Then you can change company
```

2. **If really needed (not recommended):**
```
   Bill Dispatch > Configuration > Settings
   Advanced Settings:
   Uncheck "Lock Company After Validation"
   
   WARNING: This reduces accounting controls!
```

3. **Best practice:**
```
   Don't change company after validation
   Instead:
   - Reject the invoice
   - Create new invoice in correct company
   - Better audit trail
```

---

### Problem 5: Email Reception Not Working

**Symptoms:**
- Emails sent but no invoice created
- No error message

**Solutions:**

1. **Check email alias:**
```
   Bill Dispatch > Configuration > Settings
   Verify:
   - Enable Email Reception: Checked
   - Reception Email: Correct alias
```

2. **Check incoming mail server:**
```
   Settings > Technical > Email > Incoming Mail Servers
   Verify:
   - Server is active
   - Connection working (test button)
   - Fetching emails (check last fetch date)
```

3. **Check mail alias record:**
```
   Settings > Technical > Email > Aliases
   Search for your alias (e.g., vendor.bills)
   Verify:
   - Points to account.move model
   - Default values set correctly
```

4. **Check email format:**
```
   Email must have PDF attachment
   Subject line doesn't matter
   Body text doesn't matter
   Only PDF attachment is processed
```

5. **Check logs:**
```
   Settings > Technical > Logging
   Search for errors related to "mail" or "alias"
```

---

## ✅ Best Practices

### Rule Configuration

1. **Start Simple:**
```
   Week 1: Create 5-10 core rules
   Week 2: Monitor and adjust
   Week 3: Add edge case rules
   Month 2: Optimize based on data
```

2. **Use Priority Wisely:**
```
   Priority 10-20: Most specific rules (exact vendor names)
   Priority 30-50: General rules (VAT patterns)
   Priority 60-90: Broad fallback rules (currency, country)
   Priority 100+: Last resort rules
```

3. **Test Before Activating:**
```
   Always use "Test Rule" button
   Verify it matches expected invoices
   Verify it doesn't match wrong invoices
```

4. **Document Your Rules:**
```
   Use the Description field
   Explain: Why this rule exists
   Explain: What it's supposed to catch
   Helps future administrators
```

5. **Review Monthly:**
```
   Check which rules are actually matching
   Disable unused rules
   Add rules for common manual dispatches
```

---

### Workflow Optimization

1. **Set Appropriate Thresholds:**
```
   Don't set finance threshold too low
   €1,000 threshold = CFO approves everything = bottleneck
   €10,000 threshold = CFO only approves big items = efficient
   
   Recommended by company size:
   Small company (< €1M revenue): €5,000
   Medium company (€1-10M): €10,000
   Large company (> €10M): €25,000
```

2. **Enable Notifications:**
```
   Business validators need to know when bills arrive
   Finance validators need to know when approval needed
   Configure in Settings > Notifications
```

3. **Use Bulk Approval:**
```
   Train validators to use bulk approval
   Much faster for similar invoices
   Review 10 similar invoices
   Select all
   Approve all at once
```

4. **Set Review Schedule:**
```
   Business validators: Check daily 10am
   Finance validators: Check daily 2pm
   Accountants: Post daily 4pm
   
   Establishes routine
   Prevents bottlenecks
```

---

### Data Quality

1. **Maintain Vendor Master Data:**
```
   Keep vendor records updated:
   - Correct VAT numbers
   - Current bank accounts with IBAN
   - Accurate country
   - Primary contact
   
   Good vendor data = Better rule matching
```

2. **Request Quality Scans:**
```
   Ask vendors for:
   - PDF format (not photo)
   - Original PDF from their system
   - Not printed then scanned
   - Straight orientation
   - Clear, not blurry
```

3. **Standardize Invoice Format:**
```
   Work with key vendors:
   - Request consistent format
   - Same information in same places
   - Improves OCR accuracy
```

---

### Security

1. **Principle of Least Privilege:**
```
   Don't make everyone an administrator
   Most users only need DMS User role
   Few people need Business Validator
   Even fewer need Finance Validator
```

2. **Regular Access Reviews:**
```
   Quarterly: Review who has what access
   Remove access for departed employees
   Adjust access for role changes
```

3. **Monitor Validation History:**
```
   Monthly: Review who approved what
   Look for unusual patterns
   Verify approvers are following process
```

4. **Separation of Duties:**
```
   Same person should NOT:
   - Upload invoice AND approve it
   - Approve AND post it
   
   Different people for different steps = Better control
```

---

## 📞 Support & Resources

### Getting Help

**1. Check Documentation:**
- This README (complete user guide)
- IMPLEMENTATION_GUIDE.md (deployment guide)
- Inline help text in Odoo

**2. Check Logs:**
```
Settings > Technical > Logging
Filter by "vendor_bill_dispatch"
Review error messages
```

**3. Enable Debug Mode:**
```
Settings > Activate Developer Mode
More detailed error messages
Technical menu items visible
```

### Community Resources

- Odoo Community Forums
- Odoo Documentation
- IAP Documentation for OCR

### Module Information
```
Module Name: vendor_bill_dispatch
Version: 19.0.1.0.0
Odoo Version: 19.0 Enterprise
License: LGPL-3
Author: Your Company
```

---

## 🎓 Training Resources

### Quick Start Guide (5 minutes)

**For DMS Users:**
1. Go to Bill Dispatch > Vendor Bills > OCR Draft
2. Click "Create"
3. Upload PDF invoice
4. Wait for OCR (automatic)
5. Click "Auto Dispatch" (automatic routing)
6. Done!

**For Business Validators:**
1. Go to Bill Dispatch > Vendor Bills > To Approve
2. Open invoice
3. Review content
4. Click "Business Approve" or "Reject"
5. Done!

**For Finance Validators:**
1. Go to Bill Dispatch > Vendor Bills > Finance Approval
2. Open high-value invoice
3. Review amount and approval authority
4. Click "Finance Approve"
5. Done!

**For Accountants:**
1. Open approved invoice
2. Final review of journal entries
3. Click "Post"
4. Done!

---

## 📊 Success Metrics

After implementing this module, you should see:

### Month 1 Goals:
- ✅ 50%+ invoices auto-routed
- ✅ OCR processing 80%+ of bills
- ✅ All users trained and using system
- ✅ Basic rules configured

### Month 3 Goals:
- ✅ 80%+ invoices auto-routed
- ✅ Processing time reduced 40%
- ✅ Manual data entry reduced 60%
- ✅ Complete audit trail

### Month 6 Goals:
- ✅ 90%+ invoices auto-routed
- ✅ Processing time reduced 60%
- ✅ Manual data entry reduced 80%
- ✅ User satisfaction >85%

---

## 🔄 Module Updates

### Updating the Module
```bash
# Backup first!
pg_dump your_database > backup.sql

# Update module code
cp -r vendor_bill_dispatch_new /path/to/odoo/addons/vendor_bill_dispatch

# Restart Odoo
sudo systemctl restart odoo

# Update module via command line
./odoo-bin -u vendor_bill_dispatch -d your_database

# Or via UI
Apps > Search "Vendor Bill Dispatch" > Update
```

---

## 📝 Changelog

### Version 19.0.1.0.0 (Current)
- Initial release for Odoo 19
- Complete OCR integration
- Multi-company dispatch
- Multi-level validation
- KPI dashboard
- Complete audit trail

---

## 📄 License

This module is licensed under LGPL-3.

---

## 🤝 Contributing

For bugs, suggestions, or improvements:
1. Document the issue clearly
2. Provide steps to reproduce
3. Include Odoo version and module version
4. Contact your implementation partner

---

## 🎉 Conclusion

This module transforms vendor bill processing from a manual, error-prone task into an automated, auditable workflow. With proper configuration and training, you'll see dramatic improvements in efficiency and accuracy.

**Need help?** Review the IMPLEMENTATION_GUIDE.md for step-by-step deployment instructions.

**Ready to start?** Begin with the 5-minute Quick Start Guide above!

---

**Last Updated:** February 2026
**Module Version:** 19.0.1.0.0
**For Odoo:** 19.0 Enterprise