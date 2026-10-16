export function createScamApi(callTool) {
  return {
    analyze: (text, sender = null) =>
      callTool("analyze_message", {
        text,
        sender,
      }),

    checkNumber: (number) =>
      callTool("check_number", {
        number,
      }),

    assess: (
      ownerId,
      riskScore,
      amount = null,
      payeeIsNew = false,
    ) =>
      callTool("assess_scam_risk", {
        owner_id: ownerId,
        risk_score: riskScore,
        amount,
        payee_is_new: payeeIsNew,
      }),

    openCase: ({
      ownerId,
      riskScore,
      amount,
      payeeLabel,
      payeeIsNew,
      signals = null,
      coolingOffMinutes = null,
    }) =>
      callTool("open_protection_case", {
        owner_id: ownerId,
        risk_score: riskScore,
        amount,
        payee_label: payeeLabel,
        payee_is_new: payeeIsNew,
        signals,
        cooling_off_minutes: coolingOffMinutes,
      }),

    getCase: (caseId, ownerId) =>
      callTool("get_protection_case", {
        case_id: caseId,
        owner_id: ownerId,
      }),

    getReceipt: (caseId, ownerId) =>
      callTool("get_case_receipt", {
        case_id: caseId,
        owner_id: ownerId,
      }),

    inbox: (caseId, contactId) =>
      callTool("get_family_inbox", {
        case_id: caseId,
        contact_id: contactId,
      }),

    decide: (
      caseId,
      contactId,
      code,
      decision,
    ) =>
      callTool("record_family_decision", {
        case_id: caseId,
        contact_id: contactId,
        approval_code: code,
        decision,
      }),
  };
}