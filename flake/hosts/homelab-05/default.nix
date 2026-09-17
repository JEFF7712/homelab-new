{ pkgs, ... }:
{
  imports = [
    ./disk-config.nix
    ./hardware-configuration.nix
    ../../modules/common-base.nix
    ../../modules/k3s-server.nix
    ../../modules/nvidia.nix
    ../../modules/kiosk.nix
  ];

  networking.hostName = "homelab-05";

  homelab.k3s = {
    enable = true;
    role = "agent";
    primaryInterface = "enp0s31f6";
    nodeIp = "10.0.30.15";
    serverAddress = "https://10.0.30.11:6443";
    tokenFile = "/persist/secrets/k3s-token";
  };

  security.rtkit.enable = true;
  services.pipewire = {
    enable = true;
    alsa.enable = true;
    alsa.support32Bit = true;
    pulse.enable = true;
  };

  homelab.kiosk = {
    enable = true;
    url = "http://10.0.40.13:8123/local/jarvis/index.html";
    drmDevice = "/dev/dri/card1";
    scaleFactor = "1.0";
    disableOutputs = [ "HDMI-A-2" ];
  };

  networking.firewall.extraInputRules = ''
    ip saddr { 10.0.0.0/16, 10.42.0.0/16, 100.64.0.0/10 } tcp dport 6053 accept
    ip saddr { 10.0.0.0/16, 10.42.0.0/16, 100.64.0.0/10 } tcp dport { 8095, 8097, 38801 } accept
    ip saddr { 10.0.0.0/16, 10.42.0.0/16, 100.64.0.0/10 } udp dport 5353 accept
  '';

  systemd.services.satellite-alsa-restore = {
    description = "Unmute onboard audio for Jarvis satellite";
    after = [ "sound.target" ];
    wantedBy = [ "multi-user.target" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      Restart = "on-failure";
      RestartSec = "10s";
    };
    path = [ pkgs.alsa-utils ];
    script = ''
      amixer -c 0 set Master unmute 100%
      amixer -c 0 set Headphone unmute 100%
    '';
  };

  systemd.services.satellite-combine-sink = {
    description = "Reload combined Pulse sink for Jarvis satellite";
    after = [
      "systemd-user-sessions.service"
      "satellite-alsa-restore.service"
    ];
    wantedBy = [ "multi-user.target" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      User = "kiosk";
      Restart = "on-failure";
      RestartSec = "30s";
    };
    environment = {
      XDG_RUNTIME_DIR = "/run/user/1001";
      PULSE_SERVER = "unix:/run/user/1001/pulse/native";
    };
    path = [ pkgs.pulseaudio ];
    script = ''
      for i in $(seq 1 30); do
        pactl info >/dev/null 2>&1 && break
        sleep 2
      done
      pactl info >/dev/null 2>&1 || exit 1
      if ! pactl list modules short | grep -q 'module-combine-sink.*sink_name=combined'; then
        pactl load-module module-combine-sink sink_name=combined slaves=alsa_output.usb-Kingston_HyperX_QuadCast_S_4100-00.analog-stereo,alsa_output.pci-0000_00_1f.3.pro-output-0,alsa_output.pci-0000_00_1f.3.pro-output-3,alsa_output.pci-0000_01_00.1.pro-output-3
      fi
    '';
  };

  systemd.services.satellite-hdmi-audio-clock = {
    description = "Clock HDMI-A-2 for Jarvis soundbar audio after kiosk start";
    after = [ "cage-tty1.service" ];
    wantedBy = [ "cage-tty1.service" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      User = "kiosk";
      Restart = "on-failure";
      RestartSec = "30s";
    };
    environment = {
      XDG_RUNTIME_DIR = "/run/user/1001";
      WAYLAND_DISPLAY = "wayland-0";
    };
    path = [
      pkgs.wlr-randr
      pkgs.curl
    ];
    script = ''
      for i in $(seq 1 30); do
        curl -s --max-time 5 http://127.0.0.1:9222/json | grep -q '"title": "JARVIS"' && break
        sleep 2
      done
      curl -s --max-time 5 http://127.0.0.1:9222/json | grep -q '"title": "JARVIS"' || exit 1
      if wlr-randr | grep -A1 'HDMI-A-2' | grep -q 'Enabled: no'; then
        wlr-randr --output HDMI-A-2 --on --mode 1920x1080@60.000000
      fi
    '';
  };
}
