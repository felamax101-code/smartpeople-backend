from django.db.models import FloatField,ExpressionWrapper,F
from django.db.models.functions import Power,Sqrt,Sin,Cos, Radians,ATan2
def annotate_distance(queryset,lat,lang):
    """Annotate each post with distance in km from (lat,lng)
    using the Harversine formula in pure Django ORM
    """
    lat_rad =Radians(F("location_lat"))
    lng_rad=Radians(F("location_lng"))
    user_lat=Radians(float(lat))
    user_lng=Radians(float(lng))
    dlat=lat_rad-user_lat
    dlng=lng_rad-user_lng
    
    a=(
        Power(Sin(dlat/2),2)+
        Cos(user_lat)*Cos(lat_rad)*Power(Sin(dlng/2),2)
    )
    distance_km=ExpressionWrapper(
        6371*2* ATan2(Sqrt(a),Sqrt(1-a)),
        output_field=FloatField()
    )
    return queryset.annotate(distance_km=distance_km)