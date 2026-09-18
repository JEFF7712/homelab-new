{ ... }:
{
  users.users.rupan.extraGroups = [ "netbird" ];

  services.netbird = {
    useRoutingFeatures = "server";
    clients.default = {
      port = 51820;
      name = "netbird";
      interface = "wt0";
      hardened = true;
      autoStart = true;
      login.enable = false;
    };
  };

  systemd.services.netbird = {
    after = [ "network-online.target" ];
    wants = [ "network-online.target" ];
  };

  environment.persistence."/persist".directories = [
    "/var/lib/netbird"
  ];
}
