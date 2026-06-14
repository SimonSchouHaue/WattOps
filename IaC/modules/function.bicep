targetScope = 'resourceGroup'

import { mangedIdentityType } from '../types/types.bicep'

param nameSuffix string
param location string
param managedIdentity mangedIdentityType
param InstrumentationKey string
param storageAccountName string
param deploymentStorageContainerUrl string
param serviceBusNameSpace string
param additionalAppSettings object = {}

resource appServicePlan 'Microsoft.Web/serverfarms@2025-03-01' = {
  name: 'plan-${nameSuffix}'
  location: location
  kind: 'functionapp'
  sku: {
    tier: 'FlexConsumption'
    name: 'FC1'
  }
  properties: {
    reserved: true
  }
}

resource functionApp 'Microsoft.Web/sites@2024-04-01' = {
  name: 'func-${nameSuffix}'
  location: location
  kind: 'functionapp,linux'
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentity.id}': {}
    }
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      minTlsVersion: '1.2'
    }
    keyVaultReferenceIdentity: managedIdentity.id
    functionAppConfig: {
      deployment: {
        storage: {
          type: 'blobContainer'
          value: deploymentStorageContainerUrl
          authentication: {
            type: 'UserAssignedIdentity'
            userAssignedIdentityResourceId: managedIdentity.id
          }
        }
      }
      scaleAndConcurrency: {
        maximumInstanceCount: 1
        instanceMemoryMB: 512
      }
      runtime: {
        name: 'python'
        version: '3.13'
      }
    }
  }
}

resource configAppSettings 'Microsoft.Web/sites/config@2022-09-01' = {
  name: 'appsettings'
  parent: functionApp
  properties: {
    AzureWebJobsStorage__accountName: storageAccountName
    AzureWebJobsStorage__credential: 'managedidentity'
    AzureWebJobsStorage__clientId: managedIdentity.clientId
    AZURE_CLIENT_ID: managedIdentity.clientId // Use the user assigned managed identity for Azure Authentication
    APPINSIGHTS_INSTRUMENTATIONKEY: InstrumentationKey
    APPLICATIONINSIGHTS_AUTHENTICATION_STRING: 'ClientId=${managedIdentity.clientId};Authorization=AAD'
    ServiceBusConnection__fullyQualifiedNamespace: '${serviceBusNameSpace}.servicebus.windows.net'
    ServiceBusConnection__clientId: managedIdentity.clientId
    ServiceBusConnection__credential: 'managedidentity'
    ...additionalAppSettings
  }
}
