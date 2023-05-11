# test connection
curl  --retry-connrefused --retry 10 --retry-delay 1  http://$1:5000
# test entry
curl -X POST "http://${1}:5000/entry?plate=123-123-123&parkingLot=382"
#test exit
curl -X POST "http://${1}:5000/exit?ticketId=1" 
