targetScope = 'resourceGroup'

param nameSuffix string
param location string
param servicePrincipalId string

var storageBlobDataOwnerRoleId = 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b'
var storageBlobDataContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'

var storageRoleAssignments = [storageBlobDataOwnerRoleId, storageBlobDataContributorRoleId]

resource storageAccount 'Microsoft.Storage/storageAccounts@2026-04-01' = {
  name: 'st${replace(nameSuffix, '-', '')}'
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    dnsEndpointType: 'Standard'
    minimumTlsVersion: 'TLS1_2'
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow'
    }
    publicNetworkAccess: 'Enabled'
  }
}

resource blobServices 'Microsoft.Storage/storageAccounts/blobServices@2026-04-01' = {
  name: 'default'
  parent: storageAccount
  properties: {
    deleteRetentionPolicy: {}
  }
}

resource deploymentContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2026-04-01' = {
  name: 'app-${nameSuffix}-deployment'
  parent: blobServices
  properties: {
    publicAccess: 'None'
  }
}

resource roleAssignmentStorage 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for roleId in storageRoleAssignments: {
    name: guid(storageAccount.id, servicePrincipalId, roleId)
    scope: storageAccount
    properties: {
      roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleId)
      principalId: servicePrincipalId
      principalType: 'ServicePrincipal'
    }
  }
]

output storageAccountName string = storageAccount.name
output deploymentStorageContainerUrl string = '${storageAccount.properties.primaryEndpoints.blob}${deploymentContainer.name}'
