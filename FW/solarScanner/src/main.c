#include <zephyr/kernel.h>
#include <zephyr/types.h>
#include <zephyr/sys/printk.h>
#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/hci.h>
#include <string.h>


#define TARGET_NAME "Solar_Harvester"
#define NORDIC_COMPANY_ID 0x0059

static void device_found(const bt_addr_le_t *addr, int8_t rssi,
                         uint8_t type, struct net_buf_simple *ad)
{
    char name[30] = {0};
    bool name_matched = false;

    struct bt_data data;
    struct net_buf_simple temp_ad = *ad;

    while (temp_ad.len > 1) {
        uint8_t len = net_buf_simple_pull_u8(&temp_ad);
        if (len == 0 || len > temp_ad.len) break;

        data.type = net_buf_simple_pull_u8(&temp_ad);
        data.data_len = len - 1;
        data.data = temp_ad.data;
        net_buf_simple_pull(&temp_ad, data.data_len);

        if (data.type == BT_DATA_NAME_COMPLETE || data.type == BT_DATA_NAME_SHORTENED) {
            size_t copy_len = MIN(data.data_len, sizeof(name) - 1);
            memcpy(name, data.data, copy_len);
            name[copy_len] = '\0';

            if (strcmp(name, TARGET_NAME) == 0) {
                name_matched = true;
            }
        }

        if (name_matched && data.type == BT_DATA_MANUFACTURER_DATA && data.data_len >= 4) {
            uint16_t company_id = data.data[0] | (data.data[1] << 8);
            if (company_id == NORDIC_COMPANY_ID) {
                int16_t temp_raw = data.data[2] | (data.data[3] << 8);
                int temp_int = temp_raw / 100;
                int temp_frac = temp_raw % 100;
                if (temp_frac < 0) temp_frac *= -1;
                        printk("Temp from %s: %d.%02d C (RSSI %d)\n", name, temp_int, temp_frac, rssi);
            }
        }
    }
}

void main(void)
{
    int err;

    printk("Starting BLE temperature listener...\n");

    err = bt_enable(NULL);
    if (err) {
        printk("Bluetooth init failed (err %d)\n", err);
        return;
    }

    printk("Bluetooth initialized\n");

    err = bt_le_scan_start(BT_LE_SCAN_PASSIVE, device_found);
    if (err) {
        printk("Scanning failed to start (err %d)\n", err);
        return;
    }

    printk("Scanning started\n");
}
