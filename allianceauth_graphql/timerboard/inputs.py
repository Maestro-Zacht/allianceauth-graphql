import graphene


class TimerInput(graphene.InputObjectType):
    details = graphene.String(required=True)
    system = graphene.String(required=True)
    planet_moon = graphene.String(default_value="")
    structure = graphene.Field('allianceauth_graphql.timerboard.types.TimerStructureChoices', required=True)
    timer_type = graphene.Field('allianceauth_graphql.timerboard.types.TimerTypeChoices', required=True)
    objective = graphene.Field('allianceauth_graphql.timerboard.types.TimerObjectiveChoices', required=True)
    days_left = graphene.Int(required=True)
    hours_left = graphene.Int(required=True)
    minutes_left = graphene.Int(required=True)
    important = graphene.Boolean(default_value=False)
    corp_timer = graphene.Boolean(default_value=False)
