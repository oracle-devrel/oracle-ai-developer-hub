package com.example.creditdemo.helidon;

import jakarta.annotation.PostConstruct;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.inject.Instance;
import jakarta.inject.Inject;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.sql.SQLSyntaxErrorException;
import java.sql.Statement;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;
import java.util.logging.Logger;
import org.eclipse.microprofile.config.Config;
import org.eclipse.microprofile.config.ConfigProvider;

@ApplicationScoped
public class DecisionRepository {
    private static final Logger LOGGER = Logger.getLogger(DecisionRepository.class.getName());
    private static final String DATASOURCE_URL = "javax.sql.DataSource.credit.URL";
    private static final String DATASOURCE_USER = "javax.sql.DataSource.credit.user";
    private static final String DATASOURCE_PASSWORD = "javax.sql.DataSource.credit.password";

    private final ConcurrentMap<String, CreditDecisionResponse> decisions = new ConcurrentHashMap<>();
    private final Instance<CreditDecisionDataRepository> dataRepositories;
    private CreditDecisionDataRepository dataRepository;

    @Inject
    public DecisionRepository(Instance<CreditDecisionDataRepository> dataRepositories) {
        this.dataRepositories = dataRepositories;
    }

    @PostConstruct
    void init() {
        if (dataRepositories.isResolvable()) {
            dataRepository = dataRepositories.get();
            ensureTable();
            LOGGER.info("Oracle JDBC persistence available; using Helidon Data Repository");
            return;
        }
        LOGGER.info("Oracle persistence configuration not available; using in-memory repository");
    }

    public void save(CreditDecisionResponse response) {
        if (dataRepository == null) {
            decisions.put(response.decisionId(), response);
            return;
        }
        dataRepository.insert(CreditDecisionEntity.fromResponse(response));
    }

    public Optional<CreditDecisionResponse> find(String decisionId) {
        if (dataRepository == null) {
            return Optional.ofNullable(decisions.get(decisionId));
        }
        return dataRepository.findById(decisionId).map(CreditDecisionEntity::toResponse);
    }

    public List<CreditDecisionResponse> findByCustomer(String customerId) {
        if (dataRepository == null) {
            return decisions.values().stream()
                    .filter(decision -> decision.customerId().equals(customerId))
                    .sorted(Comparator.comparing(CreditDecisionResponse::decisionId))
                    .toList();
        }
        return dataRepository.listByCustomerId(customerId)
                .stream()
                .map(CreditDecisionEntity::toResponse)
                .toList();
    }

    private void ensureTable() {
        String sql = """
                CREATE TABLE credit_decisions (
                    decision_id VARCHAR2(80) PRIMARY KEY,
                    customer_id VARCHAR2(80) NOT NULL,
                    approved NUMBER(1) NOT NULL,
                    risk_band VARCHAR2(20) NOT NULL,
                    annual_rate NUMBER(8,2) NOT NULL,
                    monthly_payment NUMBER(12,2) NOT NULL,
                    explanation VARCHAR2(500),
                    processing_millis NUMBER(12),
                    runtime VARCHAR2(80),
                    created_at TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL
                )
                """;
        Config config = ConfigProvider.getConfig();
        String url = config.getOptionalValue(DATASOURCE_URL, String.class).orElse(null);
        String user = config.getOptionalValue(DATASOURCE_USER, String.class).orElse(null);
        String password = config.getOptionalValue(DATASOURCE_PASSWORD, String.class).orElse(null);
        if (url == null || user == null || password == null) {
            throw new IllegalStateException("Oracle persistence is available but JDBC connection settings are incomplete");
        }
        try (Connection connection = DriverManager.getConnection(url, user, password);
             Statement statement = connection.createStatement()) {
            statement.execute(sql);
        } catch (SQLSyntaxErrorException e) {
            if (e.getErrorCode() == 955) {
                return;
            }
            throw new IllegalStateException("Unable to create credit_decisions table", e);
        } catch (SQLException e) {
            if (e.getErrorCode() == 955) {
                return;
            }
            throw new IllegalStateException("Unable to initialize Oracle repository", e);
        }
    }
}
