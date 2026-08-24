package com.example.creditdemo.helidon;

import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;

import java.time.Duration;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@ApplicationScoped
public class CreditDecisionService {
    private final DecisionRepository repository;

    @Inject
    public CreditDecisionService(DecisionRepository repository) {
        this.repository = repository;
    }

    public CreditDecisionResponse create(CreditDecisionRequest request) {
        CreditDecisionResponse response = evaluate(request);
        repository.save(response);
        return response;
    }

    public CreditDecisionResponse evaluate(CreditDecisionRequest request) {
        long started = System.nanoTime();
        CustomerProfile profile = lookupCustomer(request);
        double annualRate = lookupAnnualRate(request, profile);
        RiskBand riskBand = riskBand(request, profile);
        boolean approved = riskBand != RiskBand.HIGH && request.requestedAmount() <= profile.maxApprovedAmount();
        double payment = monthlyPayment(request.requestedAmount(), annualRate, request.termMonths());
        blockingPause(Duration.ofMillis(10));

        CreditDecisionResponse response = new CreditDecisionResponse(
                "D-" + UUID.randomUUID(),
                request.customerId(),
                approved,
                riskBand,
                round(annualRate),
                round(payment),
                explanation(approved, riskBand, profile),
                Duration.ofNanos(System.nanoTime() - started).toMillis(),
                "helidon-mp-4.4"
        );
        return response;
    }

    public Optional<CreditDecisionResponse> find(String decisionId) {
        return repository.find(decisionId);
    }

    public List<CreditDecisionResponse> findByCustomer(String customerId) {
        return repository.findByCustomer(customerId);
    }

    private CustomerProfile lookupCustomer(CreditDecisionRequest request) {
        blockingPause(Duration.ofMillis(35));
        double monthlyIncome = request.annualIncome() / 12.0;
        double dti = request.monthlyDebt() / monthlyIncome;
        double maxApprovedAmount = Math.max(15000, request.annualIncome() * (request.creditScore() >= 700 ? 0.65 : 0.45));
        return new CustomerProfile(dti, maxApprovedAmount);
    }

    private double lookupAnnualRate(CreditDecisionRequest request, CustomerProfile profile) {
        blockingPause(Duration.ofMillis(20));
        double baseRate = request.creditScore() >= 740 ? 6.25 : request.creditScore() >= 680 ? 8.15 : 11.75;
        return baseRate + (profile.debtToIncome() > 0.45 ? 1.25 : 0.0);
    }

    private RiskBand riskBand(CreditDecisionRequest request, CustomerProfile profile) {
        if (request.creditScore() >= 730 && profile.debtToIncome() < 0.35) {
            return RiskBand.LOW;
        }
        if (request.creditScore() >= 660 && profile.debtToIncome() < 0.50) {
            return RiskBand.MEDIUM;
        }
        return RiskBand.HIGH;
    }

    private double monthlyPayment(double principal, double annualRate, int termMonths) {
        double monthlyRate = annualRate / 100.0 / 12.0;
        return principal * monthlyRate / (1.0 - Math.pow(1.0 + monthlyRate, -termMonths));
    }

    private String explanation(boolean approved, RiskBand riskBand, CustomerProfile profile) {
        if (approved) {
            return "Approved with " + riskBand + " risk based on credit strength and debt-to-income ratio " + round(profile.debtToIncome());
        }
        return "Manual review recommended due to " + riskBand + " risk and requested amount above policy limits";
    }

    private static double round(double value) {
        return Math.round(value * 100.0) / 100.0;
    }

    private static void blockingPause(Duration duration) {
        try {
            Thread.sleep(duration);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Interrupted while simulating downstream latency", e);
        }
    }
}
