FROM --platform=linux/amd64 eclipse-temurin:25-jre
WORKDIR /app
COPY --chown=185:0 maven/target/helidon-credit-service.jar app.jar
COPY --chown=185:0 maven/target/libs libs
USER 185
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
