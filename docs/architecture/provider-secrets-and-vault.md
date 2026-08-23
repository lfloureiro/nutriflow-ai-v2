# Provider secrets and vault boundary

## Purpose

NutriFlow can discover meals from external delivery providers without storing provider credentials in application data.

Credentials are deployment secrets. They must never be written to:

- PostgreSQL application tables;
- Git or committed `.env` files;
- API responses;
- browser/local-storage state;
- recommendation run context;
- logs, traces or exception messages.

## Development secret backend

Development uses `provider_secret_backend=environment`.

Recognized secret names are deliberately references only; this document contains no secret values.

### Uber Eats

- `NUTRIFLOW_UBER_CLIENT_ID`
- `NUTRIFLOW_UBER_CLIENT_SECRET`
- activation flag: `UBER_CONSUMER_DELIVERY_ENABLED=true`

Having credentials is not sufficient to activate the adapter. Consumer Delivery access must also be approved for the application, the explicit activation flag must be enabled, and an executable Uber consumer adapter must be registered.

### Glovo

- `NUTRIFLOW_GLOVO_CLIENT_ID`
- `NUTRIFLOW_GLOVO_CLIENT_SECRET`
- activation flag: `GLOVO_CONSUMER_DISCOVERY_ENABLED=true`

Publicly documented Glovo partner APIs are not treated as a general consumer marketplace discovery contract. The consumer adapter must remain disabled until an authorized contract suitable for this use case exists.

### Bolt Food

- `NUTRIFLOW_BOLT_FOOD_INTEGRATOR_ID`
- `NUTRIFLOW_BOLT_FOOD_SECRET_KEY`
- activation flag: `BOLT_FOOD_CONSUMER_DISCOVERY_ENABLED=true`

Public Bolt Food documentation currently describes merchant/POS integration. Merchant credentials must not be repurposed to simulate consumer marketplace discovery. The consumer adapter remains disabled unless Bolt provides and authorizes that capability.

## Production vault

`ProviderSecretStore` is the application boundary for secrets. Production deployments should add one adapter appropriate to the hosting environment, for example:

- HashiCorp Vault;
- Azure Key Vault;
- AWS Secrets Manager;
- another managed secret store with equivalent access controls.

The rest of the recommendation and provider code must depend only on `ProviderSecretStore`, never directly on a specific vault SDK.

Recommended production controls:

1. one identity for the API service, no developer credentials in production;
2. least-privilege read access only to the required provider secrets;
3. secret rotation without database migrations;
4. audit logging at the vault layer;
5. no secret value in application telemetry;
6. separate provider secrets per environment;
7. provider activation flags separate from secret presence.

## Capability states

A provider is live only when all of these are true:

1. credentials are present in the active `ProviderSecretStore`;
2. consumer access is explicitly approved/enabled for the deployment;
3. an executable `MealDeliveryDiscoveryAdapter` is registered.

The capability state distinguishes:

- credentials absent;
- credentials present but consumer access not approved/enabled;
- credentials/access present but executable adapter absent;
- live adapter configured;
- public restaurant discovery independent from delivery-provider credentials.

The Web receives only safe readiness booleans (`credentials_configured`, `access_enabled`, `adapter_available`) and never receives names, values, tokens, or secret-store paths.

## External menu evidence

Provider adapters normalize observed menu items into `ExternalMenuItemObservationWrite`.

An observed item may be stored with price and availability while having no nutrition composition. Such an item is **not eligible for nutrition ranking**.

Nutrition becomes ranking-eligible only when a versioned composition exists with one of these evidence levels:

- `official` — published by the restaurant/provider as official nutrition;
- `provider` — supplied by an authorized provider feed;
- `estimated` — NutriFlow estimate, requiring an explicit confidence value.

Safety restrictions continue to fail closed when mandatory nutrient evidence is unavailable.
