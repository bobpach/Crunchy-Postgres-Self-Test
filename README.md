# Crunchy-Postgres-Self-Test
A sidecar container that tests the Crunchy Postgres for Kubernetes deployment for base functionality.

## Overview
This container is designed to run as a sidecar container in a Crunchy Data for Kubernetes Postgres pod.  The container tests base functionality and can be configured to sync an ArgoCD application to deploy the tested image to another environment.  A typical use case would be auto-promotion from dev to test if the tests pass on the dev deployment.

### Requirements:
1. Crunchy Postgres for Kubernetes 5.2 or higher
2. Python 3.11 or higher
3. See requirements.txt for additional requirements

Clone this repo to your local machine.  Start Docker if not running.

### Docker
Build
```
docker image build -t postgres-self-test:1.0.0 <path to the Dockerfile in your clone location>
```

Tag
```
docker tag postgres-self-test:1.0.0 <your registry>/postgres-self-test:1.0.0
```

Push
```
docker push <your registry>/postgres-self-test:1.0.0 
```
## Disclaimer
This container is not a comprehensive postgres testing application. It is intended to show how testing at deploy time can be used for auto-promotion in your ci/cd pipeline.  This application is not supported by Crunchy Data and is not intended to be used in production deployments.  If you choose to run this container in your environment, you do so at your own risk without any support, guarantees or warranties from Crunchy Data or any other person or organization.

## The Tests
The container runs the following tests in a Crunchy Data for Kubernetes deployment:

1. Connects to the postgres database as the configured user through the primary service.
2. Outputs the postgres version.
3. Creates a test user and a test database.
4. Switches to the test user and creates a test schema and test table with 1000 rows of randomly generated data
5. Queries the test table through the primary service and validates the row count.
6. If the cluster has replicas:
   1. Connects to the replica service, queries the test table and validates the row count.
   2. Connects to each replica pod, queries the test table and validates the row count.
7. Drops all test objects created at test time.
8. Connects to Argocd server and synchronizes an application if configured to do so.
9. Closes all open connections.

The tests run at the start of the pod and after a failover event where a new primary postgres data pod is chosen within the cluster.

Tests can also be run on demand by 'exec'ing into the selftest container and running:
```
python3 test_runner.py
```

These tests ensure that read, write, delete and replication (if applicable) processes are functioning as expected in the postgres cluster.

## Configuration
The container requires certain configuration to be set in order for it to run properly.  Each Crunchy Postgres for Kubernetes cluster being deployed will require its own configmap.  The following is a list of configuration options and a sample configmap that you can add to a deployment. 

| Property | Description | Default |
| -------- | ----------- | ------- |
| argocd-namespace | The namespace the ArgoCD server is deployed in. | argocd |
| argocd-service-address | The IP address of the argocd service to connect to. | N/A |
| argocd-verify-tls | Set to false if TLS is not used or if you are using self-signed certs. | true |
| auto-promote | Set to true if you want to auto-sync an ArgoCD application after the tests pass; else false. | false |
| auto-promote-argocd-app-name | The name of the ArgoCD application to auto-sync | N/A |
| db-user | The database user to use for the initial connection. **Must be a superuser.** | N/A |
| cluster-name | The name of the Crunchy Postgres for Kubernetes cluster being deployed. | N/A |
| log-level | Valid values: debug, info, warning, error, critical | info |
| log-path | The path of the self_test.log file to inside the volume mount. | /pgdata |
| postgres-conn-attempts | The number of connection attempts to make to the postgres database during initialization. | 12 |
| postgres-conn-interval | The number of seconds to wait until the next connection attempt. | 5 |
| service-port | The port for the postgres primary and replica services. | 5432 |
| sslmode | See [PostgreSQL Docs](https://www.postgresql.org/docs/current/libpq-ssl.html) for listing. | require |

``` yaml

apiVersion: v1
data:  
  argocd-namespace: argocd
  argocd-service-address: "127.0.0.1"
  argocd-verify-tls: "false"
  auto-promote: "true"
  auto-promote-argocd-app-name: hippo-postgres-qa
  db-user: hippo
  cluster-name: hippo
  log-level: info 
  log-path: /pgdata
  postgres-conn-attempts: "12"
  postgres-conn-interval: "5"
  service-port: "5432"
  sslmode: require
kind: ConfigMap
metadata:
  labels:
    vendor: crunchydata
    postgres-operator.crunchydata.com/cluster: hippo
  name: hippo-self-test-config

```

## Secrets
The container requires that two secrets be created in the namespace.
1. ArgoCD Token - Contains the [ArgoCD token](https://argo-cd.readthedocs.io/en/latest/user-guide/commands/argocd_account_generate-token/) to connect to the API without logging in as a user.
2. DB User Secret - The secret that contains the password for the db user.

The Crunchy Data for Kubernetes deployment will create the db user secret if you [define the user in the manifest](https://access.crunchydata.com/documentation/postgres-operator/latest/tutorial/user-management/).

## Deploying

It is assumed that you already know how to deploy Crunchy Postgres for Kubernetes.  If not please follow this [quickstart](https://access.crunchydata.com/documentation/postgres-operator/latest/quickstart/#installation).

To deploy the selftest sidecar container with your Crunchy Postgres for Kubernetes cluster you will need to do the following:

1. Enable the InstanceSidecar feature gate.  Add the following to the **spec.template.spec** section of the manager.yaml file in the operator deployment:

``` yaml
        - name: PGO_FEATURE_GATES
          value: "InstanceSidecars=true"
```
2. Apply the operator manifest
```
kubectl apply -n postgres-operator -k install/default --server-side
```
3. Apply the self-test configmap.
```
kubectl apply -n <your dev namespace> -f <your configmap>.yaml
```
4. Add the following to your **spec.instances** section of the postgres cluster deployment manifest. Substitute configmap and secret names as needed:
<details><summary>- Selftest Manifest Values</summary>

``` yaml
      containers:
        - name: selftest
          image: <your registry>/postgres-self-test:1.0.0
          imagePullPolicy: IfNotPresent
          env:
            - name: ARGOCD_APP_NAME
              valueFrom:
                configMapKeyRef:
                  name: hippo-self-test-config
                  key: auto-promote-argocd-app-name
            - name: ARGOCD_NAMESPACE
              valueFrom:
                configMapKeyRef:
                  name: hippo-self-test-config
                  key: argocd-namespace
            - name: AUTO_PROMOTE
              valueFrom:
                configMapKeyRef:
                  name: hippo-self-test-config
                  key: auto-promote
            - name: ARGOCD_SERVICE_ADDRESS
              valueFrom:
                configMapKeyRef:
                  name: hippo-self-test-config
                  key: argocd-service-address
            - name: ARGOCD_TOKEN
              valueFrom:
                secretKeyRef:
                  key: token
                  name: argocd-token
            - name: ARGOCD_VERIFY_TLS
              valueFrom:
                configMapKeyRef:
                  name: hippo-self-test-config
                  key: argocd-verify-tls
            - name: DB_USER
              valueFrom:
                configMapKeyRef:
                  name: hippo-self-test-config
                  key: db-user
            - name: DB_USER_PASSWORD
              valueFrom:
                secretKeyRef:
                  key: password
                  name: hippo-pguser-hippo
            - name: CLUSTER_NAME
              valueFrom:
                configMapKeyRef:
                  name: hippo-self-test-config
                  key: cluster-name
            - name: LOG_LEVEL
              valueFrom:
                configMapKeyRef:
                  name: hippo-self-test-config
                  key: log-level
            - name: LOG_PATH
              valueFrom:
                configMapKeyRef:
                  name: hippo-self-test-config
                  key: log-path
            - name: NAMESPACE
              valueFrom:
                fieldRef:
                  apiVersion: v1
                  fieldPath: metadata.namespace
            - name: POSTGRES_CONN_ATTEMPTS
              valueFrom:
                configMapKeyRef:
                  name: hippo-self-test-config
                  key: postgres-conn-attempts
            - name: POSTGRES_CONN_INTERVAL
              valueFrom:
                configMapKeyRef:
                  name: hippo-self-test-config
                  key: postgres-conn-interval
            - name: SERVICE_PORT
              valueFrom:
                configMapKeyRef:
                  name: hippo-self-test-config
                  key: service-port
            - name: SSLMODE
              valueFrom:
                configMapKeyRef:
                  name: hippo-self-test-config
                  key: sslmode
          volumeMounts:
          - name: postgres-data
            readOnly: false
            mountPath: /pgdata
```
</summary></details></br>

5. Apply the postgres manifest:
```
kubectl apply -n <your dev namespace> -k <your postres.yaml file>
```

6. View the postgres cluster pods.  If you have 6 containers in the postgres pods you have a successful deployment.
```
kubectl get po -n <your dev namespace>
NAME                              READY   STATUS      RESTARTS   AGE
hippo-backup-q68z-lphzn           0/1     Completed   0          104s
hippo-pgbouncer-b69b46b84-rt6c2   2/2     Running     0          2m40s
hippo-pgbouncer-b69b46b84-s4p2f   2/2     Running     0          2m40s
hippo-pgha1-j6x6-0                6/6     Running     0          2m41s
hippo-pgha1-mjw7-0                6/6     Running     0          2m41s
hippo-pgha1-xvz6-0                6/6     Running     0          2m41s
hippo-repo-host-0                 2/2     Running     0          2m40s
```

## Logs
Logs are directed to stdout, stderr and are written to the configured log path.  Here is a sample log with default log level info:
```
catcat bash-4.4$ cat /pgdata/self_test.log
2023-05-15 15:39:51,401 - self_test -           INFO - ******* STARTING NEW TEST RUN *******
2023-05-15 15:40:06,458 - self_test -           INFO - PostgreSQL database version:
2023-05-15 15:40:06,459 - self_test -           INFO - ('PostgreSQL 13.8 on x86_64-pc-linux-gnu, compiled by gcc (GCC) 8.5.0 20210514 (Red Hat 8.5.0-10), 64-bit',)
2023-05-15 15:40:06,465 - self_test -           INFO - Creating test database
2023-05-15 15:40:06,658 - self_test -           INFO - Assigning test_db privileges to test_user
2023-05-15 15:40:06,670 - self_test -           INFO - Creating test_schema in test_db
2023-05-15 15:40:06,673 - self_test -           INFO - Creating test_table with data in test_schema
2023-05-15 15:40:06,685 - self_test -           INFO - Validating DBConnectionType.PRIMARY_SERVICE Data: Expecting 1000 Rows
2023-05-15 15:40:06,686 - self_test -           INFO - *** DBConnectionType.PRIMARY_SERVICE Validation Succeeded! ***
2023-05-15 15:40:16,735 - self_test -           INFO - Validating DBConnectionType.REPLICA_SERVICE Data: Expecting 1000 Rows
2023-05-15 15:40:16,737 - self_test -           INFO - *** DBConnectionType.REPLICA_SERVICE Validation Succeeded! ***
2023-05-15 15:40:16,746 - self_test -           INFO - Validating DBConnectionType.REPLICA_POD Data for podhippo-pgha1-mjw7-0: Expecting 1000 Rows
2023-05-15 15:40:16,748 - self_test -           INFO - *** DBConnectionType.REPLICA_POD Validation Succeeded for pod hippo-pgha1-mjw7-0! ***
2023-05-15 15:40:16,761 - self_test -           INFO - Validating DBConnectionType.REPLICA_POD Data for podhippo-pgha1-xvz6-0: Expecting 1000 Rows
2023-05-15 15:40:16,763 - self_test -           INFO - *** DBConnectionType.REPLICA_POD Validation Succeeded for pod hippo-pgha1-xvz6-0! ***
2023-05-15 15:40:17,298 - self_test -           INFO - Successfully synched the hippo-postgres-qa ArgoCD application.
2023-05-15 15:40:17,298 - self_test -           INFO - ******* SUCCESS: ALL TESTS PASSED *******
2023-05-15 15:40:17,300 - self_test -           INFO - Dropping test_table
2023-05-15 15:40:17,309 - self_test -           INFO - Dropping test_schema
2023-05-15 15:40:17,314 - self_test -           INFO - Dropping test_db
2023-05-15 15:40:17,381 - self_test -           INFO - Dropping test_user
bash-4.4$
```
## Auto-Promote
If configured to do so, the selftest container will synch an argocd application to deploy the same image to another namespace.  In order for this to happen, the argocd application must be pointing to same manifest in git that is used for the dev deployment.  See my [GitOps blog](https://www.crunchydata.com/blog/postgres-gitops-with-argo-and-kubernetes) for more details.