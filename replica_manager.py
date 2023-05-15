import os
from connection_manager import ConnectionManager


class ReplicaManager:

    _replica_pod_list = None
    cm = ConnectionManager()

    @property
    def replica_pod_list(self):
        return self._replica_pod_list.items

    @property
    def has_replicas(self):
        return self.does_postgres_cluster_have_replicas()

    def get_replica_pods(self):
        """ Determine if the container is running replica data pods

        Returns:
            bool: True if Replica
        """
        # self.cm.connect_to_kubernetes()
        kube = ConnectionManager.kubernetes_connection
        ns = os.getenv('NAMESPACE')
        cluster_name = os.getenv('CLUSTER_NAME')

        replica_label = 'postgres-operator.crunchydata.com/role=replica'
        cluster_label = "postgres-operator.crunchydata.com/cluster=%s" \
            % (cluster_name)
        labels = replica_label + "," + cluster_label
        self._replica_pod_list = kube.list_namespaced_pod(
            namespace=ns, label_selector=labels)

    def does_postgres_cluster_have_replicas(self):
        if self.replica_pod_list is not None:
            if self._replica_pod_list.items is not None:
                for pod in self._replica_pod_list.items:
                    if pod is not None:
                        return True
        return False
