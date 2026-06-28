# Northwind Retail Solutions Ltd.

## Control Matrix

**Document Reference:** NSRL-CTL-2026-001
**Version:** 3.2
**Effective Date:** January 1, 2026
**Review Date:** December 31, 2026
**Prepared By:** Internal Audit Department
**Approved By:** Chief Financial Officer

---

## 1. Document Purpose and Scope

This Control Matrix establishes the framework for internal controls at Northwind Retail Solutions Ltd., a mid-sized retail and e-commerce business headquartered in Columbus, Ohio. The matrix documents the mapping between significant business processes, identified risks, control activities, responsible parties, and monitoring mechanisms.

The scope of this Control Matrix encompasses all material financial, operational, and compliance processes including:

- Revenue recognition and sales processing
- Procurement and accounts payable
- Inventory management and warehousing
- Human resources and payroll
- IT general controls and data protection
- Financial reporting and close processes

This document serves as the foundational reference for the 2026 internal audit plan and supports external audit procedures conducted by the company's independent registered public accounting firm.

---

## 2. Control Environment Overview

Northwind Retail Solutions Ltd. operates under a three-lines-of-defense model for risk management and control. The Board of Directors provides oversight through the Audit Committee. Senior Management is responsible for implementing and maintaining the control environment. The Internal Audit function provides independent assurance on the design and operating effectiveness of controls.

### 2.1 Three Lines of Defense Structure

| Line | Function | Primary Responsibilities |
|------|----------|------------------------|
| First | Business Operations | Day-to-day execution of controls within processes |
| Second | Risk Management and Compliance | Policy development, risk assessment, monitoring |
| Third | Internal Audit | Independent assurance and advisory services |

### 2.2 Control Objectives

The company maintains controls designed to achieve the following objectives:

1. **Compliance:** Adherence to applicable laws, regulations, and contractual obligations
2. **Operations:** Effective and efficient use of resources to achieve business objectives
3. **Reporting:** Reliability of internal and external financial and non-financial reports
4. **Safeguarding:** Protection of assets against loss, theft, and unauthorized use

---

## 3. Control Classification Framework

### 3.1 Control Type Definitions

| Control Type | Code | Description |
|--------------|------|-------------|
| Preventive | P | Controls designed to stop errors or irregularities before they occur |
| Detective | D | Controls designed to identify errors or irregularities after they occur |
| Corrective | C | Controls designed to correct errors or irregularities once identified |
| Manual | M | Controls requiring human intervention to execute |
| Automated | A | Controls embedded within systems executing without human intervention |
| Hybrid | H | Controls with both manual and automated components |

### 3.2 Control Rating Criteria

| Rating | Criteria | Testing Approach |
|--------|----------|-------------------|
| Critical | Material financial impact; direct regulatory requirement; loss potential exceeds $500,000 | Annual comprehensive testing with samples of 100% of population |
| High | Significant financial impact; key process control; loss potential $100,000-$500,000 | Semi-annual testing with statistical samples |
| Moderate | Moderate financial impact; supporting control; loss potential $25,000-$100,000 | Annual testing with judgmental samples |
| Low | Minimal financial impact; incidental control; loss potential below $25,000 | biennial inquiry and observation |

---

## 4. Revenue Recognition and Sales Processing Controls

### 4.1 Process Description

Revenue is recognized when control of goods transfers to customers at a point in time, typically upon shipment or delivery. The company processes approximately 15,000 sales transactions daily across retail stores, e-commerce platform, and wholesale channels.

### 4.2 Control Matrix

| Control ID | Control Description | Type | Owner | Rating | Key Risk Addressed |
|------------|---------------------|------|-------|--------|-------------------|
| REV-001 | Sales orders are validated against approved customer credit limits prior to order acceptance | P-M | Credit Manager | High | Customer defaults; revenue recognition timing |
| REV-002 | System automatically records revenue when shipping confirmation is scanned and transmitted | A | IT Operations | Critical | Manual entry errors; revenue recognition accuracy |
| REV-003 | Daily sales reconciliation comparing POS terminal totals to bank deposits | D-M | Finance Supervisor | High | Cash handling errors; theft; reconciliation gaps |
| REV-004 | Monthly review of revenue journal entries exceeding $50,000 by Controller | M | Controller | High | Unauthorized entries; misstatement |
| REV-005 | Customer returns require supervisor approval and automated credit memo generation | P-A | Operations Manager | Moderate | Fraudulent returns; margin erosion |
| REV-006 | Periodic confirmation of accounts receivable balances with customers | D-M | Credit Department | High | Receivable valuation; collectability |
| REV-007 | E-commerce transaction details automatically reconciled to payment processor records nightly | A | Finance Supervisor | Critical | Payment processing errors; fraud |
| REV-008 | Sales cut-off testing performed at month-end by external auditors | D-M | External Auditors | High | Cut-off errors; period misstatement |

### 4.3 Key Controls and Testing Procedures

**Control REV-002: Automated Revenue Recognition**

This control addresses the risk of revenue being recognized in the incorrect period or for invalid transactions. The control operates through the enterprise resource planning (ERP) system, which interfaces with the warehouse management system (WMS). When a shipping confirmation is transmitted from WMS to ERP, the system automatically creates an accounts receivable entry and recognizes revenue based on the shipping date.

Testing procedures include:

1. Inquiry with IT Operations personnel regarding system configuration
2. Observation of system processing during month-end shipping operations
3. Selection of a sample of transactions around month-end to verify cut-off
4. Examination of system logs to confirm interface completeness
5. Verification that compensating controls exist for system downtime scenarios

**Control REV-007: E-commerce Payment Reconciliation**

Given that approximately 45% of revenue is derived from e-commerce sales, the reconciliation of payment processor deposits to recorded revenue is critical. The control operates through an automated nightly batch process that compares settlement files from payment processors (Stripe, PayPal, Square) to recorded transactions.

Testing procedures include:

1. Review of reconciliation exception reports for the twelve months ended June 30, 2026
2. Inquiry regarding management's timely review and resolution of exceptions
3. Verification of user access controls to payment processor administrative functions
4. Examination of subsequent cash receipts to confirm reconciling items are resolved

---

## 5. Procurement and Accounts Payable Controls

### 5.1 Process Description

The procurement process encompasses the requisition, approval, ordering, receipt, and payment of goods and services. The company maintains approximately 2,500 active vendors and processes 3,200 invoices monthly with an average invoice value of $4,200.

### 5.2 Control Matrix

| Control ID | Control Description | Type | Owner | Rating | Key Risk Addressed |
|------------|---------------------|------|-------|--------|-------------------|
| AP-001 | Purchase orders exceeding $10,000 require Director-level approval | P-M | Department Directors | High | Unauthorized purchases; budget overruns |
| AP-002 | Vendor master file changes require Finance Manager approval and secondary review for bank account modifications | P-M | Finance Manager | Critical | Vendor fraud; payment diversion |
| AP-003 | Three-way match of purchase order, receiving report, and vendor invoice before payment processing | A-M | Accounts Payable Supervisor | High | Payment for undelivered goods; invoice errors |
| AP-004 | Blanket purchase orders reviewed quarterly for continued validity and spending patterns | D-M | Procurement Manager | Moderate | Unnecessary purchases; pricing deviations |
| AP-005 | Accounts payable aging reviewed weekly by Controller with focus on invoices over 60 days | D-M | Controller | Moderate | Vendor disputes; stale payables |
| AP-006 | Segregation of duties: invoice processing personnel cannot approve payments | P-M | AP Supervisor | High | Fraud; unauthorized payments |
| AP-007 | ACH payment runs require dual approval from Finance Manager and Controller | P-M | Finance Manager/Controller | Critical | Fraudulent payments; clerical errors |
| AP-008 | Annual vendor risk assessment conducted by Procurement and Legal | D-M | Procurement Manager | Moderate | Vendor viability; concentration risk |
| AP-009 | Segregated duties maintained between check printing and mailing functions | P-M | AP Supervisor | High | Theft; unauthorized transactions |
| AP-010 | Quarterly reconciliation of accounts payable subledger to general ledger | D-M | Accounting Supervisor | High | Recording errors; misstatement |

### 5.3 Vendor Master File Controls

The vendor master file represents a significant area of fraud risk. The company has implemented the following controls:

**New Vendor Setup:**

1. Completed W-9 form and business verification documentation required
2. Vendor added to system by Procurement with Finance Manager approval
3. Initial payments limited to $5,000 until vendor demonstrates three months of clean transactions
4. Vendor bank account changes require notarized written request and two-factor verification

**Existing Vendor Monitoring:**

1. Quarterly review of vendors with no activity in the preceding 90 days
2. Annual recertification of all active vendors exceeding $100,000 annually
3. Automated blocking of payments to vendors with mismatched tax identification numbers

---

## 6. Inventory Management and Warehousing Controls

### 6.1 Process Description

The company operates three distribution centers located in Ohio, Nevada, and Georgia, with aggregate inventory of approximately $28 million at any point in time. Inventory turns approximately 7.2 times annually. The company utilizes a perpetual inventory system with periodic cycle counts and annual physical inventory observation.

### 6.2 Control Matrix

| Control ID | Control Description | Type | Owner | Rating | Key Risk Addressed |
|------------|---------------------|------|-------|--------|-------------------|
| INV-001 | Perpetual inventory system interfaces with POS and warehouse management systems in real-time | A | IT Operations | Critical | Inventory accuracy; recording errors |
| INV-002 | Cycle counts conducted weekly for high-value items (top 20% by value) | D-M | Warehouse Managers | High | Inventory shrinkage; counting errors |
| INV-003 | Cycle counts conducted monthly for medium-value items | D-M | Warehouse Managers | Moderate | Inventory accuracy |
| INV-004 | Annual physical inventory observation with independent count observers | D-M | Internal Audit | High | Material misstatement; shrinkage |
| INV-005 | Write-offs exceeding $10,000 require Operations Director and Controller approval | P-M | Operations Director | High | Unauthorized disposals; misstatement |
| INV-006 | Inventory obsolescence reserve reviewed quarterly by Controller | D-M | Controller | High | Inventory valuation; financial reporting |
| INV-007 | Segregation of duties: warehouse personnel cannot initiate or approve inventory adjustments | P-M | Warehouse Manager | High | Fraud; unauthorized adjustments |
| INV-008 | Barcode scanning required for all inventory movements | A | Warehouse Supervisors | High | Recording accuracy; data integrity |
| INV-009 | Return-to-vendor authorizations require Returns Coordinator approval | P-M | Returns Coordinator | Moderate | Fraudulent returns; vendor disputes |
| INV-010 | Inventory aging report reviewed monthly by Merchandising Director | D-M | Merchandising Director | Moderate | Obsolete inventory; markdown requirements |

### 6.3 Shrinkage Monitoring

The company targets shrinkage below 1.5% of gross sales. Actual shrinkage for the fiscal year ended March 31, 2026 was 1.3%, representing a decrease from 1.6% in the prior year. The improvement is attributed to enhanced security tagging at retail locations and improved receiving procedures at distribution centers.

---

## 7. Human Resources and Payroll Controls

### 7.1 Process Description

The company employs 1,847 full-time and 423 part-time employees across retail stores, corporate offices, and distribution centers. Payroll is processed bi-weekly with direct deposit to employee accounts. Annual payroll is approximately $52 million.

### 7.2 Control Matrix

| Control ID | Control Description | Type | Owner | Rating | Key Risk Addressed |
|------------|---------------------|------|-------|--------|-------------------|
| HR-001 | New hire packets include mandatory background verification completion before start date | P-M | HR Coordinator | High | Hiring unqualified individuals; compliance |
| HR-002 | Payroll changes require HR Manager and Department Director dual approval | P-M | HR Manager | High | Unauthorized changes; payroll errors |
| HR-003 | Time and attendance records reconciled to scheduling system weekly | D-M | Payroll Supervisor | High | Timesheet fraud; leave abuse |
| HR-004 | Payroll tax deposits verified to third-party payroll service provider filings | D-M | Payroll Manager | Moderate | Tax compliance; filing errors |
| HR-005 | Annual benefit enrollment changes require employee signature and Benefits Manager review | P-M | Benefits Manager | Moderate | Benefit errors; compliance |
| HR-006 | Severance agreements require Legal Department review and CFO approval | P-M | Legal/CFO | High | Unfunded liabilities; compliance |
| HR-007 | Employee access rights to systems reviewed quarterly upon role changes | D-M | IT Security | High | Unauthorized access; segregation violations |
| HR-008 | Bonus and incentive calculations reviewed by Human Resources Director prior to payment | P-M | HR Director | High | Calculation errors; unauthorized payments |
| HR-009 | Segregation maintained between payroll processing and check distribution | P-M | Payroll Supervisor | High | Fraud; theft |
| HR-010 | Year-end payroll reconciliation to Form 941 filings | D-M | Payroll Manager | High | Tax compliance; W-2 accuracy |

---

## 8. IT General Controls and Data Protection

### 8.1 Control Framework

The company's IT general controls are designed in accordance with the Control Objectives for Information and Related Technologies (COBIT) framework and support the Trust Services Criteria established by the American Institute of Certified Public Accountants (AICPA).

### 8.2 Control Matrix

| Control ID | Control Description | Type | Owner | Rating | Key Risk Addressed |
|------------|---------------------|------|-------|--------|-------------------|
| IT-001 | User access rights reviewed quarterly by system owners and documented in access logs | D-M | IT Security Manager | High | Unauthorized access; segregation violations |
| IT-002 | Production system changes require documented business justification, testing, and IT Director approval | P-M | IT Director | High | System integrity; data loss |
| IT-003 | Backup restoration testing performed semi-annually with results reported to IT Steering Committee | D-M | IT Operations | High | Data recoverability; business continuity |
| IT-004 | Incident response procedures documented and tested annually | D-M | IT Security Manager | High | Security breaches; data protection |
| IT-005 | Change management logs reconciled to implementation records monthly | D-M | IT Audit Liaison | Moderate | Completeness; unauthorized changes |
| IT-006 | Logical access to financial systems requires annual recertification by system owners | P-M | IT Security Manager | High | Access governance; segregation |
| IT-007 | End-user computing tools (Excel, Access) used for financial reporting subject to version control and backup | P-M | Department Directors | Moderate | Data integrity; version control |
| IT-008 | Vendor access to systems limited and monitored with automated logging | P-M | IT Security Manager | Critical | External threats; data security |
| IT-009 | Data classification performed annually with protective controls aligned to classification level | P-M | Data Governance Officer | High | Data protection; regulatory compliance |
| IT-010 | Business continuity and disaster recovery plans tested annually with executive sign-off | D-M | IT Director | High | Operational resilience; recovery capabilities |

---

## 9. Financial Reporting and Close Process Controls

### 9.1 Control Description

The monthly financial close process is completed within five business days following month-end. The company prepares quarterly and annual financial statements in accordance with U.S. Generally Accepted Accounting Principles (GAAP).

### 9.2 Control Matrix

| Control ID | Control Description | Type | Owner | Rating | Key Risk Addressed |
|------------|---------------------|------|-------|--------|-------------------|
| FR-001 | Journal entries require department manager approval; entries exceeding $25,000 require Controller approval | P-M | Department Managers/Controller | High | Unauthorized entries; misstatement |
| FR-002 | Account reconciliations prepared monthly for all balance sheet accounts with balances exceeding $10,000 | D-M | Accounting Staff | High | Reconciliation errors; misstatement |
| FR-003 | Intercompany accounts reconciled and eliminated monthly | D-M | Accounting Supervisor | High | Consolidation errors; misstatement |
| FR-004 | Management review of financial statements includes ratio analysis and variance to budget | D-M | Controller | High | Material misstatement; analytical anomalies |
| FR-005 | Disclosure checklist completed for quarterly and annual reporting periods | D-M | Controller | High | Completeness; regulatory compliance |
| FR-006 | Restatement trigger analysis performed by external auditors quarterly | D-M | External Auditors | High | Materiality; disclosure requirements |
| FR-007 | Fixed asset register reconciled to general ledger monthly | D-M | Accounting Supervisor | High | Asset accuracy; depreciation |
| FR-008 | Accrual accounts reviewed and adjusted as necessary prior to financial statement preparation | P-M | Accounting Staff | High | Expense recognition; liability completeness |
| FR-009 | Deferred revenue schedules reviewed for proper recognition timing | D-M | Revenue Manager | High | Revenue recognition; liabilities |
| FR-010 | Related party transactions disclosed in quarterly financial statements | D-M | Controller | Critical | Transparency; regulatory compliance |

---

## 10. Monitoring and Continuous Improvement

### 10.1 Control Monitoring Activities

The Internal Audit Department maintains responsibility for ongoing monitoring of the control environment. Monitoring activities include:

1. **Continuous Auditing:** Automated audit routines executed weekly against transaction populations to identify anomalies requiring follow-up

2. **Control Self-Assessment:** Quarterly control self-assessment questionnaires distributed to control owners to confirm control operating effectiveness

3. **Key Risk Indicator Reporting:** Monthly dashboard reporting of control metrics including exception rates, aged items, and reconciliation variances

4. **Independent Testing:** Annual comprehensive testing of all Critical and High-rated controls; rotation of Moderate-rated control coverage over two-year cycle

### 10.2 Deficiency Reporting and Remediation

Control deficiencies are classified as follows:

| Classification | Materiality Threshold | Reporting Requirement |
|---------------|---------------------|--------------------|
| Significant Deficiency | Could reasonably result in misstatement that is less than material but warrants attention | Reported to Audit Committee within 30 days |
| Material Weakness | Reasonable possibility that controls will not prevent or detect misstatement at material level | Reported to Audit Committee within 10 business days; disclosed in annual report |

All identified control deficiencies require a documented remediation plan with responsible party, target completion date, and evidence of remediation upon completion.

### 10.3 Document Maintenance

This Control Matrix is reviewed annually and updated as necessary to reflect changes in business processes, risk assessments, regulatory requirements, and audit findings. Version control is maintained through the document management system with all superseded versions archived.

---

## Appendix A: Control Owner Index

| Role | Name | Department |
|------|------|------------|
| Chief Financial Officer | Marcus Chen | Finance |
| Controller | Sarah Williams | Finance |
| Finance Manager | David Park | Finance |
| Accounting Supervisor | Jennifer Martinez | Finance |
| Accounts Payable Supervisor | Robert Thompson | Finance |
| Credit Manager | Amanda Foster | Finance |
| IT Director | Kevin O'Brien | Information Technology |
| IT Security Manager | Michelle Rodriguez | Information Technology |
| IT Operations Manager | Brian Anderson | Information Technology |
| Human Resources Director | Lisa Patel | Human Resources |
| Benefits Manager | James Wilson | Human Resources |
| Payroll Manager | Patricia Lee | Human Resources |
| Operations Director | Christopher Brown | Operations |
| Warehouse Manager | Stephanie Garcia | Operations |
| Merchandising Director | Daniel Kim | Merchandising |
| Procurement Manager | Nicole Taylor | Procurement |
| Returns Coordinator | Matthew Johnson | Operations |
| Data Governance Officer | Rachel Adams | Information Technology |

---

## Appendix B: Document Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 3.2 | January 1, 2026 | Internal Audit | Updated for 2026 fiscal year; added IT-010 business continuity testing |
| 3.1 | July 1, 2025 | Internal Audit | Incorporated vendor payment fraud controls (AP-002 revision) |
| 3.0 | January 1, 2025 | Internal Audit | Comprehensive revision; added three-lines-of-defense model |
| 2.0 | January 1, 2024 | Internal Audit | Expansion of IT general controls section |
| 1.0 | January 1, 2023 | Internal Audit | Initial release |

---

**Document Classification:** Internal Use Only
**Next Review Date:** December 31, 2026
**Document Owner:** Chief Financial Officer
**Contact:** internal.audit@northwindretail.com
