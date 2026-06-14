targetScope = 'resourceGroup'

param nameSuffix string
param location string
param servicePrincipalId string
param queueName string

var serviceBusDataReceiverRoleId = '4f6d3b9b-027b-4f4c-9142-0e5a2a2247e0'
var serviceBusDataSenderRoleId = '69a216fc-b8fb-44d8-bc22-1f3c2cd27a39'

var roleAssignments = [serviceBusDataReceiverRoleId, serviceBusDataSenderRoleId]

resource serviceBusNamespace 'Microsoft.ServiceBus/namespaces@2024-01-01' = {
  name: 'sbns-${nameSuffix}'
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {}
}

resource serviceBusQueues 'Microsoft.ServiceBus/namespaces/queues@2024-01-01' = {
  parent: serviceBusNamespace
  name: queueName
  properties: {
    maxSizeInMegabytes: 1024
    requiresDuplicateDetection: false
    requiresSession: false
    defaultMessageTimeToLive: 'P1D' // 1 day
    deadLetteringOnMessageExpiration: true
    duplicateDetectionHistoryTimeWindow: 'PT10M' // 10 minutes
    maxDeliveryCount: 10
    enablePartitioning: false
    enableExpress: false
  }
}

resource roleAssignmentServiceBus 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for roleId in roleAssignments: {
    name: guid(serviceBusNamespace.id, servicePrincipalId, roleId)
    scope: serviceBusNamespace
    properties: {
      roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleId)
      principalId: servicePrincipalId
      principalType: 'ServicePrincipal'
    }
  }
]

output serviceBusNamespace string = serviceBusNamespace.name
