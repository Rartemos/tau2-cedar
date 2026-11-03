permit (
    principal is TelecomAgent,
    action == Action::"provideTechnicalSupport",
    resource is SupportRequest
) when {
    resource.withinActionScope &&
    resource.customerIdentified
};

permit (
    principal is TelecomAgent,
    action == Action::"sendPaymentRequest",
    resource is Bill
) when {
    context.request.withinActionScope &&
    resource.isOverdue
};

permit (
    principal is TelecomAgent,
    action == Action::"suspendLine",
    resource is Line
) when {
    context.request.withinActionScope &&
    resource.status == LineStatus::"Active"
};

permit (
    principal is TelecomAgent,
    action == Action::"providePlanOptions",
    resource is SupportRequest
) when {
    resource.withinActionScope
};

permit (
    principal is TelecomAgent,
    action == Action::"transferToHumanAgents",
    resource is SupportRequest
) when {
    !resource.withinActionScope &&
    resource.resolutionOptionsExhausted &&
    !(resource.activeToolCallCount > 0) &&
    !resource.responseInProgress
};

permit (
    principal is TelecomAgent,
    action == Action::"respondToUser",
    resource is SupportRequest
) when {
    context.message == "YOU ARE BEING TRANSFERRED TO A HUMAN AGENT." &&
    resource.humanTransferCompleted &&
    context.usesOnlyUserOrToolInformation &&
    !context.containsSubjectiveRecommendationsOrComments &&
    !(resource.activeToolCallCount > 0)
};

permit (
    principal is TelecomAgent,
    action == Action::"denyRequest",
    resource is SupportRequest
) when {
    context.requestViolatesPolicy
};

permit (
    principal is TelecomAgent,
    action == Action::"checkBillStatus",
    resource is Bill
);

permit (
    principal is TelecomAgent,
    action == Action::"checkBillAmountDue",
    resource is Bill
);

permit (
    principal is TelecomAgent,
    action == Action::"makePayment",
    resource is PaymentRequest
) when {
    resource.accepted &&
    resource.bill.status == BillStatus::"Awaiting Payment"
};

permit (
    principal is TelecomAgent,
    action == Action::"resumeLine",
    resource is Line
) when {
    resource.status == LineStatus::"Suspended"
};

permit (
    principal is TelecomAgent,
    action == Action::"refuelData",
    resource is Line
) when {
    resource.status == LineStatus::"Active" &&
    context.amountGB.greaterThan(decimal("0.0")) &&
    context.amountGB.lessThanOrEqual(decimal("2.0")) &&
    context.plan.planId == resource.planId &&
    context.cumulativeRefuelingWithinLimit &&
    context.billingMatchesLinePlanPrice
};

permit (
    principal is TelecomAgent,
    action == Action::"changePlan",
    resource is Line
) when {
    context.supportRequest has providedPhoneNumber &&
    context.supportRequest.providedPhoneNumber == resource.phoneNumber &&
    context.supportRequest has selectedPlan &&
    context.supportRequest.selectedPlan.planId != resource.planId &&
    context.supportRequest has calculatedPlanPrice
};

permit (
    principal is TelecomAgent,
    action == Action::"calculatePlanPrice",
    resource is Plan
) when {
    context.supportRequest has providedPhoneNumber &&
    context.line.phoneNumber == context.supportRequest.providedPhoneNumber &&
    context.supportRequest has selectedPlan &&
    context.supportRequest.selectedPlan == resource &&
    resource.planId != context.line.planId
};

permit (
    principal is TelecomAgent,
    action == Action::"checkRoamingStatus",
    resource is Line
) when {
    context.outsideHomeNetwork
};

permit (
    principal is Customer,
    action == Action::"checkStatusBar",
    resource is Device
) when {
    resource.customer == principal
};

permit (
    principal is Customer,
    action == Action::"checkNetworkStatus",
    resource is Device
) when {
    resource.customer == principal
};

permit (
    principal is Customer,
    action == Action::"checkWifiCallingStatus",
    resource is Device
) when {
    resource.customer == principal
};

permit (
    principal is Customer,
    action == Action::"checkAppPermissions",
    resource is App
) when {
    resource.device.customer == principal
};

permit (
    principal is Customer,
    action == Action::"runSpeedTest",
    resource is Device
) when {
    resource.customer == principal
};

permit (
    principal is Customer,
    action == Action::"canSendMms",
    resource is App
) when {
    resource.device.customer == principal
};

permit (
    principal is Customer,
    action == Action::"setNetworkModePreference",
    resource is Device
) when {
    resource.customer == principal
};

permit (
    principal is Customer,
    action == Action::"toggleAirplaneMode",
    resource is Device
) when {
    resource.customer == principal
};

permit (
    principal is Customer,
    action == Action::"toggleData",
    resource is Device
) when {
    resource.customer == principal
};

permit (
    principal is Customer,
    action == Action::"reseatSimCard",
    resource is Device
) when {
    resource.customer == principal
};

permit (
    principal is Customer,
    action == Action::"toggleRoaming",
    resource is Device
) when {
    resource.customer == principal
};

permit (
    principal is Customer,
    action == Action::"toggleDataSaverMode",
    resource is Device
) when {
    resource.customer == principal
};

permit (
    principal is Customer,
    action == Action::"toggleWifi",
    resource is Device
) when {
    resource.customer == principal
};

permit (
    principal is Customer,
    action == Action::"toggleWifiCalling",
    resource is Device
) when {
    resource.customer == principal
};

permit (
    principal is Customer,
    action == Action::"disconnectVpn",
    resource is Device
) when {
    resource.customer == principal
};

permit (
    principal is Customer,
    action == Action::"grantAppPermission",
    resource is App
) when {
    resource.device.customer == principal
};

permit (
    principal is Customer,
    action == Action::"rebootDevice",
    resource is Device
) when {
    resource.customer == principal
};

permit (
    principal is Customer,
    action == Action::"checkSimStatus",
    resource is Device
) when {
    resource.customer == principal
};

permit (
    principal is Customer,
    action == Action::"checkApnSettings",
    resource is Device
) when {
    resource.customer == principal
};

permit (
    principal is Customer,
    action == Action::"resetApnSettings",
    resource is Device
) when {
    resource.customer == principal &&
    !resource.apnSettingsCorrect
};

permit (
    principal is TelecomAgent,
    action == Action::"verifyServiceRestored",
    resource is Line
) when {
    resource.status == LineStatus::"Suspended"
};

permit (
    principal is TelecomAgent,
    action == Action::"checkLineStatus",
    resource is Line
);

permit (
    principal is Customer,
    action == Action::"checkDataRestrictionStatus",
    resource is Device
) when {
    resource.customer == principal
};

permit (
    principal is Customer,
    action == Action::"checkVpnStatus",
    resource is Device
) when {
    resource.customer == principal
};

permit (
    principal is Customer,
    action == Action::"connectVpn",
    resource is Device
) when {
    resource.customer == principal
};

permit (
    principal is Customer,
    action == Action::"checkNetworkModePreference",
    resource is Device
) when {
    resource.customer == principal
};

permit (
    principal is TelecomAgent,
    action == Action::"lookupCustomerByPhoneNumber",
    resource is Customer
) when {
    context.phoneNumber == resource.phoneNumber
};

permit (
    principal is TelecomAgent,
    action == Action::"lookupCustomerByCustomerId",
    resource is Customer
) when {
    context.customerId == resource.customerId
};