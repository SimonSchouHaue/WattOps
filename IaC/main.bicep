targetScope = 'subscription'

import { environmentType } from 'types/types.bicep'

@description('Location for all resources')
param location string
@description('Environment for the deployment (e.g. dev, prod)')
param environment environmentType
@description('Name of the queue')
param queueName string
@description('Additional application settings besides the Azure configuration values')
param additionalAppSettings object
@description('Suffix for resource names')
param nameSuffix string
@description('Name of the azure key vault to store secrets')
param keyVaultName string

resource rg 'Microsoft.Resources/resourceGroups@2025-04-01' = {
  name: 'rg-infrastructure-${environment}'
  location: location
}

module function 'modules/function.bicep' = {
  name: 'function-module'
  scope: rg
  params: {
    nameSuffix: nameSuffix
    location: location
    deploymentStorageContainerUrl: storageAccountModule.outputs.deploymentStorageContainerUrl
    InstrumentationKey: loggingModule.outputs.InstrumentationKey
    serviceBusNameSpace: serviceBusModule.outputs.serviceBusNamespace
    managedIdentity: managedIdentityModule.outputs.managedIdentity
    storageAccountName: storageAccountModule.outputs.storageAccountName
    additionalAppSettings: additionalAppSettings
  }
}

module keyVaultModule 'modules/keyVault.bicep' = {
  name: 'key-vault-module'
  scope: rg
  params: {
    keyVaultName: keyVaultName
    location: location
    servicePrincipalId: managedIdentityModule.outputs.managedIdentity.servicePrincipalId
  }
}

module loggingModule 'modules/logging.bicep' = {
  name: 'logging-module'
  scope: rg
  params: {
    nameSuffix: nameSuffix
    location: location
    servicePrincipalId: managedIdentityModule.outputs.managedIdentity.servicePrincipalId
  }
}

module managedIdentityModule 'modules/managedIdentity.bicep' = {
  name: 'managed-identity-module'
  scope: rg
  params: {
    nameSuffix: nameSuffix
    location: location
  }
}

module serviceBusModule 'modules/serviceBus.bicep' = {
  name: 'service-bus-module'
  scope: rg
  params: {
    nameSuffix: nameSuffix
    location: location
    servicePrincipalId: managedIdentityModule.outputs.managedIdentity.servicePrincipalId
    queueName: queueName
  }
}

module storageAccountModule 'modules/storageAccount.bicep' = {
  name: 'storage-account-module'
  scope: rg
  params: {
    nameSuffix: nameSuffix
    location: location
    servicePrincipalId: managedIdentityModule.outputs.managedIdentity.servicePrincipalId
  }
}
