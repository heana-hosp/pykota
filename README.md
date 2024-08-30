# Pykota
Git Repository to Pykota - Version updated to Python 3

This repository was created to update the pykota project and adapt it to Python version 3.12(upgraded) or higher.

### Features
 - Updated the version to work with python version 3.12(upgraded) or higher;

### Considerations
 - This version was tested only on Postgres Database;
 - We adapt in order to meet personal demands;
 - Only the pkipplib, pkpgcounter and pykota projects have been migrated to version 3.12(updated) or higher;
 - The tea4cups project have not migrated at the moment and we don't know if we will update. The pykotaicon project will be updated soon.




### Simple tutorial - Installation Pykota with Ubuntu Server 24.04 LTS and PostgreSQL(Upgraded)

#### With fresh install Ubuntu Server 24.04 LTS and upgrade all packages ... and get power of root.. let's go.


Clone repository:
```bash
cd /opt
```
```bash
git clone https://github.com/heana-hosp/pykota.git
```

*Get the power of root and proceed to install - every command with permission*

Install CUPS Service:
```bash
apt install cups
```
Easy way to get exception on apparmor for CUPS:
```bash
apt install apparmor-utils
```
```bash
aa-complain cupsd
```
```bash
/etc/init.d/apparmor restart
```

Check version of python - must be equal to or higher than 3.12:
```bash
python3 --version
```
Install PostgreSQL:
```bash
apt install postgresql postgresql-contrib
```

Install Python libs needed to this version:
```bash
apt install python3-pil python3-pypdf2 libpq-dev python3.12-dev python3-psycopg2 python3-reportlab python3-build python3-venv python3-pip
```

#### Build and Install Pykota libs, tools, configuration and database.
#### Obs: This build process has been updated since the last version. The name of the package built in the dist directory may vary depending on the parameters defined in pyproject.toml

1 - Install pkipplib:
```bash
cd /opt/pykota/pkipplib/
```
```bash
python3 -m build
```
```bash
pip3 install dist/pkipplib-1.0.0-py3-none-any.whl --break-system-packages
```

2 - Install pkpgcounter:
```bash
cd /opt/pykota/pkpgcounter/
```
```bash
python3 -m build
```
```bash
pip3 install dist/pkpgcounter-4.0.0-py3-none-any.whl  --break-system-packages
```

3 - Install pykota:

Check dependencies before:
```bash
cd /opt/pykota/pykota/
```
```bash
python3 checkdeps.py
```

*Check the output if some libs were detected - in this case, the library for postgres and pkpgcounter(in previous step) was correctly installed.*
 
>...<BR>
>Checking for Python-Psycopg availability : OK<BR>
>...<BR>
>...<BR>
>Checking for Python-pkpgcounter availability : OK<BR>
>... <BR>

Build and Install:
```batch
python3 -m build
```

```batch
pip3 install dist/pykota-1.0.0-py3-none-any.whl  --break-system-packages
```
Generate database:
```batch
su - postgres -c "psql -f  /opt/pykota/pykota/initscripts/postgresql/pykota-postgresql.sql template1"`
```
*By default, the database passwords are already defined for the pykotauser and pykotaadmin users(after generate script). If you need to change the password, change it at the database and don't forget to update passwords on files pykota.conf and pykotadmin.conf on directory /etc/pykota (instructions ahead).*


Copy backend from pykota to cups libs and give permissions:
```batch
cp /opt/pykota/pykota/bin/cupspykota /usr/lib/cups/backend/
```
```batch
chmod -R 755 /usr/lib/cups/backend/cupspykota
```
Restart Cups:
```batch
systemctl restart cups
```
Create user pykota on system:
```batch
adduser --system --group --home /etc/pykota --gecos PyKota pykota
```
Copy default configuration files and set permission:
```batch
cp /opt/pykota/pykota/conf/pykota.conf.sample /etc/pykota/pykota.conf
```
```batch
cp /opt/pykota/pykota/conf/pykotadmin.conf.sample /etc/pykota/pykotadmin.conf
```
```batch
chmod 755 /etc/pykota
```
```batch
chmod 644 /etc/pykota/pykota.conf
```
```batch
chmod 644 /etc/pykota/pykotadmin.conf
```
```batch
chown pykota:pykota /etc/pykota/pykota.conf /etc/pykota/pykotadmin.conf
```


Adjust the correct path to pkpgcounter and pknotify in the /etc/pykota/pykota.conf file

Check the path:
```bash
which pkpgcounter 
```
> /usr/local/bin/pkpgcounter <BR>

```bash
which pknotify
```
> /usr/local/bin/pknotify <BR>

Change lines or comment - pknotify will return to client a prompt message(pykotaicon on client):


>...<BR>
>accounter : software(/usr/local/bin/pkpgcounter)<BR>
>...<BR>
>preaccounter: software(/usr/local/bin/pkpgcounter)<BR>
>...<BR>
>askconfirmation : /usr/local/bin/pknotify --destination $PYKOTAJOBORIGINATINGHOSTNAME:7654 --timeout 7 --confirm "Hello $PYKOTAUSERNAME.\nThe job  $PYKOTAJOBID will be send to $PYKOTAPRINTERNAME and cost $PYKOTAPRECOMPUTEDJOBSIZE page(s)\nYour balance is $PYKOTABALANCE\n\nDo you really want to print?"<BR>
><BR>

#### Configure CUPS and add printer.

Reference Guide: https://ubuntu.com/server/docs/service-cups

Change JobPrivateAccess to **all** on `<Policy default>`

Change JobPrivateValues to **none** on `<Policy default>`

On `<Location />` and `<Location /admin>` add **Allow IP_STATION_WILL_CONFIGURE_PRINTERS**

Example: If I want to access the server remotely from IP 100.100.100.133 - follow the configuration section of the file:


>...<BR>
><Location /><BR>
  >Order allow,deny<BR>
  >Allow 100.100.100.133<BR>
></Location><BR>
><BR>
>\# Restrict access to the admin pages...<BR>
><Location /admin><BR>
  >Order allow,deny<BR>
  >Allow 100.100.100.133<BR>
></Location><BR>
><BR>
>\# Restrict access to configuration files...<BR>
><Location /admin/conf><BR>
  >AuthType Default<BR>
  >Require user @SYSTEM<BR>
  >Order allow,deny<BR>
></Location><BR>
><BR>
>\# Restrict access to log files...<BR>
><Location /admin/log><BR>
  >AuthType Default<BR>
  >Require user @SYSTEM<BR>
  >Order allow,deny<BR>
></Location><BR>
><BR>
><BR>
>\# Set the default printer/job policies...<BR>
><Policy default><BR>
>  \# Job/subscription privacy...<BR>
>  JobPrivateAccess all<BR>
>  JobPrivateValues none<BR>
>  SubscriptionPrivateAccess default<BR>
>  SubscriptionPrivateValues default<BR>
>...<BR>


Add lpadmin group
```bash
usermod -a -G  lpadmin $USER
```
Restart CUPS
```bash
systemctl restart cups
```
Add printer on CUPS:

In the browser(emember the IP assigned in the cups configuration file) access **IP_SERVER:631**

**Administration -> Add Printer -> Login with user from linux(root) and password -> Option: Other Network Printers -> IPP -> Continue;**

Add backend cupspykota on connection: change ipp to **cupspykota:ipp://IP_PRINTER** -> continue to next step;

Give a Name, Description, Localization and mark Share this printer and continue. **Important:** The name is sensitive case, and will be used the same text to define printer on pykota.

Configure the driver for your print. Recomended the postscripts/cupsfilter drivers. You can find optimized driver ppd on internet for specified printer. Finally complete the installation.

#### Add user and printer on pykota

Add printer(remember, case sensitive: same name of printer installed on cups). Ex. name is TEST:
```bash
pkprinters --add TEST
```
Add user and set balance. In this case, the user is the same user who is logged in to the Windows station. To find out who the user is. just run (echo %USERNAME%) in cmd. In this example we will use **testuser**:
```bash
pkusers --add usertest
```

Defining the balance type for the user and defining a balance. Pykota allows you to assign the balance and quota type. Next step, give 50 balance.
```bash
pkusers --limitby balance usertest
```
```bash
pkusers --balance +50.0 --comment "add more 50!" usertest
```
Link user: testuser to printer: TEST
```bash
edpykota --add usertest
```
```bash
edpykota --printer TEST -S 50 -H 50 usertest
```
#### Add printer in Windows

win + r (Execute) -> control printers

Add printer -> The printer is not in the list ->  Select Printer Shared by Name:

format: `http://IP_SERVER:631/printers/NAME_PRINTER_CREATED_CUPS`

Ex. http://IP_SERVER:631/printers/TEST

After proceeding, you will be directed to the driver installation wizard and complete instalation.

#### Execute pykoticon on host Windows

Download example client windows from oficial site:

http://www.pykota.com/software/pykoticon/download/tarballs/pykoticon-1.02.zip

Extract to any directory

Edit the file pykoticon.vbs

Change the line `retcode = Wshshell.run ("%comspec% /C pykoticon.exe --port 7654 nordine.ateur", 0, FALSE)`

Assign the IP of the server you just installed: `retcode = Wshshell.run ("%comspec% /C pykoticon.exe --port 7654 IP_FROM_PYKOTA_SERVER", 0, FALSE)`

Save and run the application pykoticon.exe. The icon will appear in the tray icon. Now just send a print for testing.

































