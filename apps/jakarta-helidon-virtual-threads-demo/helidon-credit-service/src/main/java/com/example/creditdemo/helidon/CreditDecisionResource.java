package com.example.creditdemo.helidon;

import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.NotFoundException;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.PathParam;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;

import java.util.List;
import java.util.Map;
import java.util.logging.Logger;

@Path("/")
@ApplicationScoped
@Consumes(MediaType.APPLICATION_JSON)
@Produces(MediaType.APPLICATION_JSON)
public class CreditDecisionResource {
    private static final Logger LOGGER = Logger.getLogger(CreditDecisionResource.class.getName());

    private final CreditDecisionService service;

    @Inject
    public CreditDecisionResource(CreditDecisionService service) {
        this.service = service;
    }

    @POST
    @Path("/credit-decisions")
    public CreditDecisionResponse create(CreditDecisionRequest request) {
        LOGGER.info(() -> "credit decision create requested customerId=" + request.customerId()
                + " amount=" + request.requestedAmount());
        return service.create(request);
    }

    @POST
    @Path("/credit-decisions/evaluate")
    public CreditDecisionResponse evaluate(CreditDecisionRequest request) {
        LOGGER.info(() -> "credit decision evaluate requested customerId=" + request.customerId()
                + " amount=" + request.requestedAmount());
        return service.evaluate(request);
    }

    @GET
    @Path("/credit-decisions/{decisionId}")
    public CreditDecisionResponse get(@PathParam("decisionId") String decisionId) {
        LOGGER.info(() -> "credit decision lookup requested decisionId=" + decisionId);
        return service.find(decisionId).orElseThrow(() -> new NotFoundException("Decision not found"));
    }

    @GET
    @Path("/credit-decisions/customer/{customerId}")
    public List<CreditDecisionResponse> byCustomer(@PathParam("customerId") String customerId) {
        LOGGER.info(() -> "customer decisions requested customerId=" + customerId);
        return service.findByCustomer(customerId);
    }

    @GET
    @Path("/health/simple")
    public Map<String, String> health() {
        LOGGER.info("health check requested");
        return Map.of("status", "UP", "runtime", "helidon-mp-4.4");
    }
}
