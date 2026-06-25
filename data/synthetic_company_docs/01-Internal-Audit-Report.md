# Internal Audit Report

**Northwind Retail Solutions Ltd.**

**Internal Audit Department**

---

**Document Reference:** IA-2026-004
**Report Date:** June 18, 2026
**Audit Period:** January 1, 2025 – December 31, 2025
**Classification:** Internal Use – Confidential
**Distribution:** Board of Directors, Audit Committee, Chief Financial Officer, Chief Operating Officer

---

## 1. Executive Summary

This Internal Audit Report presents the findings, observations, and recommendations resulting from the internal audit of Northwind Retail Solutions Ltd. ("the Company") for the fiscal year ended December 31, 2025. The audit was conducted in accordance with the Internal Audit Charter approved by the Board of Directors on March 15, 2023, and followed the International Standards for the Professional Practice of Internal Auditing promulgated by the Institute of Internal Auditors (IIA).

The scope of this audit encompassed the Company's retail operations, e-commerce platform, financial reporting processes, inventory management controls, and IT general controls. Our examination was conducted with the objective of providing independent assurance on the adequacy and effectiveness of the Company's risk management, control environment, and governance processes.

**Overall Audit Opinion:** The internal control environment of Northwind Retail Solutions Ltd. is generally adequate but requires targeted improvements in inventory accuracy, e-commerce transaction processing, and IT access management. No material control failures were identified; however, several moderate-risk observations warrant management attention within the next 90 days.

---

## 2. Audit Scope and Methodology

### 2.1 Scope of Work

The audit covered the following functional areas and business processes:

| Audit Area | Processes Covered | Key Controls Reviewed |
|------------|-------------------|----------------------|
| Retail Operations | Point-of-sale transactions, cash handling, end-of-day reconciliation | Segregation of duties, dual authorization, daily reconciliation |
| E-commerce Platform | Order processing, payment gateway integration, fulfillment | Transaction logging, PCI-DSS compliance, order verification |
| Inventory Management | Stock receipts, warehouse transfers, cycle counts, shrinkage | Perpetual inventory records, authorization protocols, count procedures |
| Financial Reporting | Revenue recognition, accounts receivable, period-end closes | Cut-off testing, journal entry approval, account reconciliation |
| IT General Controls | Access management, change management, backup and recovery | Role-based access, change approval board, backup verification |

### 2.2 Audit Methodology

The audit methodology employed a risk-based approach consistent with the Company's Internal Audit Plan for 2025. The methodology included:

- **Risk Assessment:** Identification and evaluation of inherent risks within each audited process, considering both likelihood and potential business impact.
- **Control Testing:** Walkthroughs of key processes, examination of supporting documentation, and substantive testing of transactions selected via statistical sampling.
- **Control Effectiveness Evaluation:** Assessment of whether existing controls are designed appropriately and operating effectively to mitigate identified risks.
- **Compliance Testing:** Verification of adherence to Company policies, regulatory requirements, and industry standards including PCI-DSS and applicable IFRS pronouncements.

Sampling was performed using monetary unit sampling (MUS) for transaction-oriented tests and judgmental sampling for process and control observations. The audit team conducted 47 interviews with process owners, control operators, and senior management. Documentary evidence comprising 312 items was reviewed and archived.

---

## 3. Audit Findings and Observations

### 3.1 Findings Summary

The audit identified 14 observations during the audit period, categorized by risk rating as follows:

| Risk Rating | Count | Description |
|-------------|-------|-------------|
| Critical | 0 | None identified |
| High | 2 | E-commerce payment reconciliation gaps, IT privileged access concentration |
| Moderate | 7 | Inventory count discrepancies, journal entry override controls, vendor master data changes |
| Low | 5 | Documentation gaps, minor policy deviations |

The two high-risk findings require immediate management action as detailed below.

---

### 3.2 High-Risk Observations

#### Finding 2025-H-001: E-Commerce Payment Reconciliation Gap

**Area:** E-commerce Platform – Order-to-Cash Process
**Risk Rating:** High
**Initial Detection Date:** February 14, 2025
**Control Reference:** CTR-ECOM-015 (Payment Gateway Reconciliation)

**Observation:**
During our examination of e-commerce transaction processing, we identified a significant gap in the daily reconciliation between the Company's e-commerce platform (Northwind Online) and its third-party payment processor (SecurePay Gateway). Testing of 85 randomly selected transactions revealed that 12 transactions (14.1%) did not have a corresponding settlement record in the payment gateway within the required five-business-day window.

The reconciliation process currently relies on manual extraction of transaction logs from Northwind Online and comparison against SecurePay settlement files. The Company's reconciliation procedure (FIN-PROC-022) specifies that reconciling items must be investigated within three business days; however, log reviews indicated that 9 of the 12 unreconciled items exceeded the investigation window by an average of 11 calendar days.

**Root Cause:**
The reconciliation process has not been updated to reflect the increased transaction volume following the Company's 2024 e-commerce expansion. The current manual process is insufficient for the volume of approximately 4,200 daily transactions. Additionally, automated alerting thresholds were not configured to escalate unresolved items beyond 7 days.

**Potential Impact:**
Failure to timely identify and resolve payment discrepancies could result in revenue misstatement, customer disputes, and potential regulatory scrutiny. The extended resolution timeline increases the risk that fraudulent transactions may not be detected within an acceptable window.

**Recommendation:**
1. Implement automated reconciliation tooling that matches transaction-level records between Northwind Online and SecurePay Gateway on a near-real-time basis.
2. Establish escalation triggers that notify the Treasury Manager and Financial Controller when reconciling items remain unresolved beyond three business days.
3. Revise FIN-PROC-022 to incorporate updated volume thresholds and automated controls.
4. Conduct a retrospective review of all unreconciled items from the past 12 months to quantify potential exposure.

**Management Response:**
The Chief Financial Officer acknowledges this finding. A project to implement automated reconciliation tooling has been initiated with an expected completion date of September 30, 2026. In the interim, the Treasury Manager has implemented weekly senior review of all unresolved items. The retrospective review will be completed by July 31, 2026.

**Target Implementation Date:** September 30, 2026

---

#### Finding 2025-H-002: IT Privileged Access Concentration

**Area:** IT General Controls – Access Management
**Risk Rating:** High
**Initial Detection Date:** March 3, 2025
**Control Reference:** CTR-IT-008 (Privileged Access Review)

**Observation:**
Our access rights review identified that privileged access to the Company's core ERP system (Oracle Fusion) is concentrated among three individuals within the IT Department: the IT Director, the Senior Database Administrator, and the ERP Security Analyst. While the Company maintains documented policies requiring annual access reviews (IT-POL-003), the most recent access certification was performed 18 months ago, in December 2024, and did not include formal recertification for the privileged role holders.

Furthermore, access logging for privileged actions within Oracle Fusion is configured with a 90-day retention period, which is below the Company's stated requirement of 12 months as specified in IT-POL-012 (Data Retention Standard). Audit log evidence for the period prior to October 2025 has been automatically purged per the prior retention schedule.

**Root Cause:**
The access recertification process does not incorporate a mechanism to trigger recertification when personnel changes occur within privileged role assignments. The retention schedule mismatch between IT-POL-012 and the system configuration resulted from a change implementation in August 2024 that was not subject to formal change advisory board review.

**Potential Impact:**
Concentration of privileged access without timely recertification increases the risk of unauthorized system changes, data integrity issues, and potential abuse. The inability to review historical privileged actions for the period prior to October 2025 limits the audit team's ability to investigate potential control violations during that timeframe.

**Recommendation:**
1. Implement quarterly privileged access recertification as a compensating control pending remediation of access concentration.
2. Engage an independent third party to perform a one-time review of privileged access assignments and justification documentation.
3. Correct the Oracle Fusion audit log retention configuration to comply with the 12-month requirement in IT-POL-012.
4. Establish a formal handoff protocol for privileged access that requires dual authorization and immediate recertification upon role changes.

**Management Response:**
The IT Director concurs with this finding. Quarterly recertification will commence immediately. The third-party review will be initiated by July 1, 2026. The Oracle Fusion retention configuration will be corrected by June 30, 2026. The handoff protocol will be developed and implemented by August 15, 2026.

**Target Implementation Date:** September 30, 2026

---

### 3.3 Moderate-Risk Observations

#### Finding 2025-M-001: Inventory Cycle Count Discrepancies

**Area:** Inventory Management
**Risk Rating:** Moderate
**Control Reference:** CTR-INV-007 (Cycle Count Program)

Testing of the warehouse cycle count program identified variances exceeding the Company's tolerance threshold (±0.5% of inventory value) in 6 of 23 count locations tested. The aggregate variance was $47,832 (representing 0.73% of tested inventory value), which exceeds the documented tolerance. Variances were concentrated in the Company's Distribution Center located in Memphis, Tennessee, and the e-commerce fulfillment warehouse in Dallas, Texas.

#### Finding 2025-M-002: Journal Entry Approval Override

**Area:** Financial Reporting
**Risk Rating:** Moderate
**Control Reference:** CTR-FIN-011 (Journal Entry Approval)

A sample of 150 journal entries was reviewed to evaluate compliance with the three-level approval requirement for entries exceeding $25,000. Eleven entries (7.3%) in the sample did not exhibit evidence of Level 2 approval as required by Company policy. All 11 entries were subsequently approved upon review; however, the lack of contemporaneous approval represents a control deviation.

#### Finding 2025-M-003: Vendor Master Data Maintenance

**Area:** Procurement and Accounts Payable
**Risk Rating:** Moderate
**Control Reference:** CTR-PROC-004 (Vendor Onboarding)

Review of 30 newly added vendors in the Company's master vendor file revealed that 4 vendors (13.3%) were established without documented procurement manager approval, and 2 vendors lacked required W-9 documentation on file prior to first payment processing. These deviations expose the Company to risk of unauthorized vendor relationships and potential IRS reporting penalties.

#### Finding 2025-M-004: IT Change Management Documentation

**Area:** IT General Controls – Change Management
**Risk Rating:** Moderate
**Control Reference:** CTR-IT-015 (Change Advisory Board)

Testing of 18 production changes implemented during the audit period revealed that 3 changes (16.7%) lacked complete documentation of change advisory board (CAB) approval. The three changes were classified as emergency changes and were implemented under the expedited approval pathway; however, post-implementation documentation did not include evidence of emergency authorization by the IT Director as required by IT-PROC-009.

#### Finding 2025-M-005: Customer Order Authorization

**Area:** E-commerce Operations
**Risk Rating:** Moderate
**Control Reference:** CTR-ECOM-008 (Order Credit Review)

Analysis of credit memos issued for e-commerce orders during Q4 2025 (the Company's highest-volume quarter) identified 34 orders totaling $23,450 that were released to fulfillment without completing the automated credit review. The orders were subsequently cancelled prior to shipment in 28 cases; however, 6 orders (totaling $4,120) were fulfilled and resulted in credit memos being issued to customers. While the aggregate financial exposure is not material, the control bypass represents a process deviation that could expose the Company to increased fraud risk during peak periods.

#### Finding 2025-M-006: Physical Security Access Review

**Area:** Physical Security and Asset Protection
**Risk Rating:** Moderate
**Control Reference:** CTR-SEC-003 (Badge Access Recertification)

The Company's badge access system currently supports 847 active employee badges, 112 contractor badges, and 38 visitor badges. Access rights reviews are performed annually; however, during our review, we identified 7 terminated employees whose badges remained active in the system for an average of 14 calendar days following their separation date. Human Resources and IT Security coordination procedures for badge deactivation require improvement to ensure timely revocation.

#### Finding 2025-M-007: Segregation of Duties – Accounts Payable

**Area:** Accounts Payable and Treasury
**Risk Rating:** Moderate
**Control Reference:** CTR-FIN-018 (AP Segregation)

The accounts payable function currently has two staff members who both have the ability to create vendors in the master file and initiate payments via the treasury management system. While the Company has a policy requiring different individuals to perform these functions, the current staffing level in the AP department does not support full segregation. The Financial Controller performs a monthly review of all payments as a compensating control; however, this detective control is not sufficient to fully mitigate the inherent risk of a single individual having end-to-end payment authority.

---

### 3.4 Low-Risk Observations

Five low-risk observations were identified during the audit, relating to documentation gaps in standard operating procedures (3 findings), minor deviations from the Company's travel and expense policy (1 finding), and a training record deficiency for one IT security awareness module (1 finding). These observations have been communicated to the relevant process owners and do not require formal tracking in the issues management system.

---

## 4. Prior Audit Follow-Up

The internal audit department conducted follow-up procedures on observations from the prior internal audit (Report IA-2025-003, dated June 20, 2025). The following table summarizes the status of prior findings:

| Finding Reference | Description | Status | Comments |
|-------------------|-------------|--------|----------|
| 2024-H-001 | IT Backup Restoration Testing | Partially Remediated | Restoration tests performed quarterly; documentation improvement needed |
| 2024-M-002 | Accounts Receivable Aging Review | Fully Remediated | New monthly aging review process implemented and operating effectively |
| 2024-M-003 | Procurement Card Controls | Fully Remediated | Enhanced monitoring controls implemented |
| 2024-L-001 | Policy Documentation Currency | Fully Remediated | Annual review cycle established |

---

## 5. Audit Committee and Management Responsibilities

The internal audit function is independent and objective, providing assurance to the Audit Committee and Board of Directors on the adequacy and effectiveness of Northwind Retail Solutions Ltd.'s risk management, control environment, and governance processes. The findings and recommendations in this report represent the professional judgment of the internal audit team based on the work performed.

Management is responsible for establishing and maintaining adequate internal controls over the areas audited and for implementing appropriate procedures to address the observations identified in this report. The Audit Committee oversees management's implementation of corrective actions and receives quarterly updates on remediation progress.

---

## 6. Next Scheduled Audit

The next scheduled internal audit engagement will be the Annual Financial Statement Audit Support review, scheduled to commence in September 2026. This engagement will provide internal audit assistance to the Company's external auditors and focus on areas with higher inherent risk of material misstatement, including revenue recognition, inventory valuation, and accounts receivable collectability.

---

## 7. Acknowledgments

The internal audit team gratefully acknowledges the cooperation and assistance provided by management and staff throughout the audit engagement. We appreciate the candor and responsiveness of the IT Director, Chief Financial Officer, and Financial Controller in addressing our inquiries and providing requested documentation.

---

**Internal Audit Team:**

Margaret L. Thornton, CIA, CRMA – Internal Audit Director
James R. Okafor, CISA – Senior Internal Auditor
Priya K. Nair, CPA – Internal Auditor
David S. Chen, CIA – Internal Auditor (IT Specialist)

---

**Document Control:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | June 18, 2026 | M. Thornton | Initial issuance |
| 1.1 | June 20, 2026 | M. Thornton | Minor editorial corrections per management review |

---

*This document contains confidential information intended solely for the use of Northwind Retail Solutions Ltd. Unauthorized disclosure, reproduction, or distribution is prohibited.*
