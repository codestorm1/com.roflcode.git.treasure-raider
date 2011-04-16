export PYTHONPATH=${PYTHONPATH}:/users/bryan/projects/treasure_raider/app/apps

cd /users/Bryan/projects/treasure_raider/app/apps/treasure_raider/loaders

tr '\r' '\n' < config.csv > cfg.csv
appcfg.py upload_data --url=http://localhost:8080/remote_api --has_header --email=twistedogre@gmail.com --config_file=config_loader.py --filename=cfg.csv --kind=Config /users/bryan/projects/treasure_raider/app
cp cfg.csv config.csv
rm cfg.csv

