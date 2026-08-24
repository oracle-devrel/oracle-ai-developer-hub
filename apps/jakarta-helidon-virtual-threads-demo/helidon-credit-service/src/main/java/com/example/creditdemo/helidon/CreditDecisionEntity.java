package com.example.creditdemo.helidon;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "credit_decisions")
public class CreditDecisionEntity {
    @Id
    @Column(name = "decision_id", length = 80, nullable = false)
    private String decisionId;

    @Column(name = "customer_id", length = 80, nullable = false)
    private String customerId;

    @Column(name = "approved", nullable = false)
    private boolean approved;

    @Enumerated(EnumType.STRING)
    @Column(name = "risk_band", length = 20, nullable = false)
    private RiskBand riskBand;

    @Column(name = "annual_rate", nullable = false)
    private double annualRate;

    @Column(name = "monthly_payment", nullable = false)
    private double monthlyPayment;

    @Column(name = "explanation", length = 500)
    private String explanation;

    @Column(name = "processing_millis")
    private long processingMillis;

    @Column(name = "runtime", length = 80)
    private String runtime;

    public CreditDecisionEntity() {
    }

    private CreditDecisionEntity(CreditDecisionResponse response) {
        this.decisionId = response.decisionId();
        this.customerId = response.customerId();
        this.approved = response.approved();
        this.riskBand = response.riskBand();
        this.annualRate = response.annualRate();
        this.monthlyPayment = response.monthlyPayment();
        this.explanation = response.explanation();
        this.processingMillis = response.processingMillis();
        this.runtime = response.runtime();
    }

    public static CreditDecisionEntity fromResponse(CreditDecisionResponse response) {
        return new CreditDecisionEntity(response);
    }

    public CreditDecisionResponse toResponse() {
        return new CreditDecisionResponse(
                decisionId,
                customerId,
                approved,
                riskBand,
                annualRate,
                monthlyPayment,
                explanation,
                processingMillis,
                runtime
        );
    }
}
