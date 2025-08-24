# ResourceTracking
This repository contains the code for a website and demon that tracks the resource management of our lab servers.

Once a new commit has been pushed to the development server, one needs to re-reun the following commands as the deploy user on cortex: 

sudo systemctl reload nginx 
sudo systemctl restart webservice_res
