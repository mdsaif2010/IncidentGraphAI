
from falkordb import FalkorDB

db = FalkorDB(host="localhost", port=6379)
graph = db.select_graph("incidents")

# Reset demo graph so this script can be run repeatedly
graph.query("MATCH (n) DETACH DELETE n")

# Create a realistic sample incident graph
graph.query("""
CREATE
  (frontend:Service {name: 'Frontend'}),
  (payment:Service {name: 'Payment'}),
  (database:Service {name: 'Database'}),
  (inventory:Service {name: 'Inventory'}),
  (deploy:Deployment {
    id: 'deploy-042',
    service: 'Payment',
    version: '2.4.0',
    status: 'failed',
    time: '10:42'
  }),
  (alert:Alert {
    id: 'alert-101',
    severity: 'critical',
    message: 'Payment error rate above 20%'
  }),
  (incident:Incident {
    id: 'INC-1042',
    title: 'Checkout failures',
    status: 'investigating'
  }),
  (frontend)-[:CALLS]->(payment),
  (payment)-[:CALLS]->(database),
  (frontend)-[:CALLS]->(inventory),
  (deploy)-[:DEPLOYED_TO]->(payment),
  (alert)-[:AFFECTS]->(payment),
  (incident)-[:TRIGGERED_BY]->(alert),
  (incident)-[:INVOLVES]->(payment)
RETURN incident.id AS incident, deploy.id AS deployment
""")

print("IncidentGraph AI demo graph created!")

result = graph.query("""
MATCH (a)-[r]->(b)
RETURN labels(a)[0] AS from_type,
       coalesce(a.name, a.id) AS from_node,
       type(r) AS relationship,
       coalesce(b.name, b.id) AS to_node
""")

for row in result.result_set:
    print(f"{row[0]}: {row[1]} --{row[2]}--> {row[3]}")
