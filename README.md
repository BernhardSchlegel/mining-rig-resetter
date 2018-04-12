# Mining rig resetter

Automatically resets your rig after it froze. It is done using the mining pools
API based on the "last seen" value. Based on that, local WiFi switches are
automatically turned off and on. The whole script is freely parameterizable
using a `config.json` file. Runs on a [Rapsberry Pi](http://amzn.to/2tDxQ1x).

This work would have not been possible without the awesome reverse engineering job
from the guys from [softscheck.com](https://www.softscheck.com/en/reverse-engineering-tp-link-hs110/).
For the full story, check out [Reverse Engineering the TP-Link HS110](https://www.softscheck.com/en/reverse-engineering-tp-link-hs110/) or visit
their [project on  github](https://github.com/softScheck/tplink-smartplug).

## Setup

- Install Python 3.5 (I recommend using [Anaconda](https://www.continuum.io/downloads) in case you dont have Python on your
  system yet.
- Clone this repo, e.g. to the Desktop of Raspberry (`git clone https://github.com/BernhardSchlegel/mining-rig-resetter.git`).
- Modify the `config.json` to match your setup. Detailled information is provieded
  below in the [Configuration](#Configuration) section.
- navigate to directory and run it using Python 3: `python rig-resetter.py`
- You're done.

## Configuration

A minimal config will look like this:

    {
      "time_before_first_run_min": 0,
      "main_cycle_time_minutes": 10,
      "on_queue_cycle_seconds": 5,
      "pools": [
        {
          "json_url": "https://api.ethermine.org/miner/6635f43003cbb97eb50a36427b6a08e288b16520/workers",
          "rigs": [
            {
              "name": "default1",
              "name_field": "worker",
              "time_field": "lastSeen",
              "ip": "192.168.49.42",
              "timeout_minutes": 15,
              "distance_seconds": 10,
              "grace_minutes": 10
            }
          ]
        }
      ]
    }

- `setting_time_before_first_run_min`: Time in minutes before main loop where the
  REST api is requested is executed for the first time. 2 minutes are recommended
  if you're using WiFi. If you're connected using a Ethernet cable you can set this
  to 0.
- `main_cycle_time_minutes`: This determines the frequency the API from
  the pool will be queried. Usually 10 minutes works fine. Setting the value too
  low will result in the API blocking you (to avoid DDoS).
- `on_queue_cycle_seconds`: Sets how often the "turning back on" loop
  runs. So if this is set to `5`, the script will check every 5 seconds if there
  are rigs due to turned on again.
- `pools`: An array holding multiple pool objects. Every pool object has to have
   the following properties:
- `json_url`: The URL to your API. In most cases you will just have to set your
   walled address - anything else can stay the same.
- `rigs`: An array of objects that describe your rig. Every rig has to have the
   following properties:
- `name`: Name of the rig. This is used for logging and for accessing the API.
- `name_field`: This determines the name of the field where the rig-resetter will
   search for the name. `worker` is fine for ethermine.
- `time_field`: sets how the field is called where the last share submit time is
   responded. `lastSeen` is fine for ethermine.
- `ip`: IP of the WiFi switch in your lokal network. If you have trouble figuring
   this out, see Section [Finding out the IP](#finding-out-the-ip).
- `timeout_minutes`: If the last submit time of this worker was longer ago than
   the specified minutes in this field, your rig will be resetted.
- `distance_seconds`: How many seconds will be rig be in the "off" state before
   being turned on again by the script. Some Mainboards require the AC power to
   be off for a couple of seconds before the reboot after the AC power loss.
- `grace_minutes`: Give the worker some time to boot up before you kill him again.
   This will protect the worker from being resetted until the grace periode is over.


### Finding out the ip

Of course you can brute force / port scan - but this is the gentle way (how I did it):

1. First, we need to find out the MAC address. Look it up in the (Kasa) app like so:
1. Then, go to the devices screen of your router. Look up, which IP adress (e.g.
   `192.168.178.42` belongs to the MAC-Adress (e.g. `50:C7:BF:BD:9A:F4`) we
   identified in the last step.
1. Set this as <IP> in the config-file.


## Supported pools and WiFi switches

### Pools

- [ethermine.org](https://ethermine.org/)
- [zcash.flypool.org](http://zcash.flypool.org/)
- [etc.ethermine.org](https://etc.ethermine.org/)
- If you want to add a pool, send me a pull request. I'm happy with ethermine atm.

### WiFi Switches

- [TP-Link HS100](http://amzn.to/2tGy4sN)
- [TP-Link HS110](http://amzn.to/2utluf2)
- If you want to add a switch, send me a pull request or the hardware.

## Setting up on a Raspberry Pi to run on startup

1. Open the terminal (<kbd>Ctrl</kbd>+<kbd>Alt</kbd>+<kbd>T</kbd>) if you hooked up your Raspberry Pi to a display or ssh to your Raspberrry Pi.
1. Change directory to Desktop `cd Desktop` and create a new folder `mkdir wd`, open that folder `cd wd`.
1. Clone the repo using `git clone https://github.com/BernhardSchlegel/mining-rig-resetter`.
1. change to ssh directory `cd /home/pi/Desktop/wd/mining-rig-resetter/ssh`.
1. Sanitize line breaks, just to be sure: `tr -d '\r' < launcher.sh > launcher_new.sh & mv launcher_new.sh launcher.sh`.
1. Open crontab using `crontab -e`.
1. If you're editing crontab the first time, a question will pop up, asking for your preffered editor. Go with nano (using <kbd>2</kbd> and <kbd>Return</kbd>).
1. Paste `@reboot sh /home/pi/Desktop/wd/mining-rig-resetter/ssh/launcher.sh >/home/pi/Desktop/wd/mining-rig-resetter/ssh/cronlog 2>&1` to the end of the file and add a blank line afterwards.
1. exit using <kbd>Ctrl</kbd>+<kbd>X</kbd>, confirming with <kbd>Y</kbd> and <kbd>Return</kbd>
1. Download & install Anaconda frome [here](https://repo.continuum.io/archive/Anaconda3-4.2.0-Linux-x86_64.sh) using `bash ./Anaconda3-4.2.0-Linux-x86_64.sh`.

## TODO

- [ ] Reset based on hashrate
- [ ] Colors in console.
- [ ] Ease the setup-process.
- [ ] Add power usage logging.
- [ ] Add hashrate logging.
