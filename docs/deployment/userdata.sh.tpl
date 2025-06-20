userdata.sh.tpl
	symstemctl
	journalctl
	inline systemd file

# 1. Deploy infrastructure (if not already done)
cd infrastructure/terraform
tofu apply

# 2. Run manual deploy
./scripts/deploy-to-s3.sh

# 3. SSH and manually update (feel the pain!)
ssh ubuntu@<ip>
# ... manual commands ...

# 4. Create tunnel and test
ssh -L 8080:localhost:8080 ubuntu@<ip>

# 3. SSH and manually update (feel the pain!)
  ssh ubuntu@<ip>

  # Once logged in, you need to:

  # a) Find out what bucket name was created
  aws s3 ls | grep crucible-deployment

  # b) Download the latest package
  cd /home/ubuntu
  aws s3 cp s3://dev-crucible-deployment-ACCOUNTID
  /latest.tar.gz crucible-latest.tar.gz

  # c) Create a new directory for the new version
  mkdir crucible-new

  # d) Extract the package
  tar -xzf crucible-latest.tar.gz -C crucible-new

  # e) Backup the current version (just in case)
  if [ -d crucible ]; then
      mv crucible crucible-backup-$(date
  +%Y%m%d-%H%M%S)
  fi

  # f) Move new version into place
  mv crucible-new crucible

  # g) Restart the service
  sudo systemctl restart crucible-platform

  # h) Check if it worked
  sudo systemctl status crucible-platform

  # i) Watch the logs to make sure it's running
  sudo journalctl -u crucible-platform -f

  # If something went wrong, restore backup:
  # mv crucible crucible-broken
  # mv crucible-backup-20250113-123456 crucible
  # sudo systemctl restart crucible-platform

  That's 10+ manual steps, each with potential for
   typos or mistakes. And you have to remember the
   exact sequence every time!


   sudo cat /etc/systemd/system/crucible-platform.service | grep -A5 -B5 "ProtectSystem\|PrivateTmp"

   cd /home/ubuntu/crucible
  ./venv/bin/python app.py --port 8080