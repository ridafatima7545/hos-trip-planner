from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import TripPlannerService, TripPlanningError


class PlanTripView(APIView):
    def post(self, request):
        try:
            result = TripPlannerService().plan(request.data)
        except TripPlanningError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"detail": "Unable to plan this trip.", "debug": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(result)
