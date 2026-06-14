targetScope = 'resourceGroup'

import { mangedIdentityType } from '../types/types.bicep'

param nameSuffix string
param location string

resource userAssignedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2024-11-30' = {
  name: 'id-${nameSuffix}'
  location: location
}

output managedIdentity mangedIdentityType = {
  id: userAssignedIdentity.id
  clientId: userAssignedIdentity.properties.clientId
  servicePrincipalId: userAssignedIdentity.properties.principalId
}
