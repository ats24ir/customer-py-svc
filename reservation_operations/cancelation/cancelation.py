# reservation_operations/cancel_reserve.py
from models import *
from datetime import datetime
from redis_om.model.model import NotFoundError

def cancel_reservation(time: str, date: str, service_name: str, artist_name: str, customer_name: str, salon_name: str):
    datetime_str = f"{date} {time}"
    datetime_obj = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")

    try:
        time_block = TimeBlocks.find(
            (TimeBlocks.time == datetime_obj.strftime("%Y-%m-%d %H:%M")) &
            (TimeBlocks.service.name == service_name) &
            (TimeBlocks.artist == artist_name) &
            (TimeBlocks.salon == salon_name)
        ).first()
    except NotFoundError:
        return {"error": "Time slot not found"}

    if time_block.available:
        return {"error": "Time slot is not reserved"}

    try:
        customer = Customers.find(Customers.name == customer_name).first()
    except NotFoundError:
        return {"error": "Customer not found"}

    # Save cancellation details
    canceled_reservation = CanceledReservations(
        time=time_block.time,
        salon=time_block.salon,
        artist=time_block.artist,
        service=time_block.service,
        customer=customer,
        cancellation_time=datetime.now()
    )
    canceled_reservation.save()

    # Mark the time block as available
    time_block.available = True
    time_block.customer = None
    time_block.save()

    return {"success": "Reservation canceled successfully"}
cancel_reservation("09:00", "2024-11-17", "Service1", "Artist 6", "Customer 1", "Salon 0")
print("reservation cancelled and the data added to the canceled reservation list")