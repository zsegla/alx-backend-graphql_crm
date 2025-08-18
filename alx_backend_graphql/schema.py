import graphene
from crm.schema import Query as CRMQuery, Mutation as CRMMutation


class Query(graphene.ObjectType):
    hello = graphene.String(default_value="Hello, GraphQL!")
   

class Mutation(CRMMutation, graphene.ObjectType):
    pass

schema = graphene.Schema(query=Query, mutation=Mutation)