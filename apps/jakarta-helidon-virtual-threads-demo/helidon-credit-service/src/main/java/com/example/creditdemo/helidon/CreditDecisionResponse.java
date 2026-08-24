package com.example.creditdemo.helidon;

public record CreditDecisionResponse(
        String decisionId,
        String customerId,
        boolean approved,
        RiskBand riskBand,
        double annualRate,
        double monthlyPayment,
        String explanation,
        long processingMillis,
        String runtime
) {
}
