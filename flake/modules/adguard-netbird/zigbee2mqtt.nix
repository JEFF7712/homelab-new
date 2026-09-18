{ pkgs, ... }:
{
  services.zigbee2mqtt = {
    enable = true;
    settings = {
      version = 5;
      homeassistant.enabled = true;
      permit_join = false;
      mqtt = {
        server = "mqtt://10.0.30.10:1883";
        user = "!secret.yaml mqtt_user";
        password = "!secret.yaml mqtt_password";
      };
      serial = {
        adapter = "ember";
        port = "/dev/serial/by-id/usb-SONOFF_SONOFF_Dongle_Lite_MG21_048030cb64a2ef11b809926661ce3355-if00-port0";
      };
      advanced = {
        channel = 25;
        network_key = "!secret.yaml network_key";
      };
    };
  };

  systemd.services.zigbee2mqtt-secrets = {
    before = [ "zigbee2mqtt.service" ];
    requiredBy = [ "zigbee2mqtt.service" ];
    unitConfig.ConditionPathExists = "/persist/secrets/zigbee2mqtt-secret.yaml";
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
    };
    script = ''
      ${pkgs.coreutils}/bin/install -m 0600 -o zigbee2mqtt -g zigbee2mqtt \
        /persist/secrets/zigbee2mqtt-secret.yaml /var/lib/zigbee2mqtt/secret.yaml
    '';
  };

  environment.persistence."/persist".directories = [
    "/var/lib/zigbee2mqtt"
  ];
}
