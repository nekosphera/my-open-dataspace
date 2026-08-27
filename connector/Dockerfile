FROM eclipse-temurin:21-jdk AS builder

# install Maven in builder image
RUN apt-get update && \
    apt-get install -y maven && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy pom.xml and download dependencies
COPY pom.xml .
RUN mvn dependency:resolve

# Copy source code and build
COPY src src
RUN mvn clean package -DskipTests

# Runtime stage
FROM eclipse-temurin:21-jre

ARG VCS_REF=unknown
ARG BUILD_DATE=unknown
LABEL org.opencontainers.image.source="https://github.com/nekosphera/my-open-dataspace" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.title="My Open Dataspace connector"

WORKDIR /app

# Copy jar from builder
COPY --from=builder /build/target/edc-identity-hub-integration-jar-with-dependencies.jar application.jar

# Copy configuration
COPY config/ config/

# Expose ports
EXPOSE 8080 9090 9091

# Run the application
ENTRYPOINT ["java", "-jar", "application.jar"]
