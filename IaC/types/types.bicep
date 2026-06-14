@export()
type environmentType = 'dev' | 'test' | 'prod'

@export()
type mangedIdentityType = {
  id: string
  clientId: string
  servicePrincipalId: string
}
