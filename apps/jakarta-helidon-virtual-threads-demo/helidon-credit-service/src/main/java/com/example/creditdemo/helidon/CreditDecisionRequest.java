package com.example.creditdemo.helidon;

public record CreditDecisionRequest(
        String customerId,
        double requestedAmount,
        int termMonths,
        double annualIncome,
        double monthlyDebt,
        int creditScore
) {
}
