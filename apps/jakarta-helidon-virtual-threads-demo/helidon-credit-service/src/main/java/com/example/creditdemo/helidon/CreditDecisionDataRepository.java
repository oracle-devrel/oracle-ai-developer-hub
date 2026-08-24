package com.example.creditdemo.helidon;

import io.helidon.data.Data;

import java.util.List;

@Data.Repository
public interface CreditDecisionDataRepository extends Data.CrudRepository<CreditDecisionEntity, String> {
    @Data.Query("SELECT d FROM CreditDecisionEntity d WHERE d.customerId = :customerId ORDER BY d.decisionId")
    List<CreditDecisionEntity> listByCustomerId(String customerId);
}
