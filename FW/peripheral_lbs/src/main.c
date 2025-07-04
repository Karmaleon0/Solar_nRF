/*
 * Copyright (c) 2018 Nordic Semiconductor ASA
 *
 * SPDX-License-Identifier: LicenseRef-Nordic-5-Clause
 */

#include <zephyr/types.h>
#include <stddef.h>
#include <string.h>
#include <math.h>

#include <zephyr/sys/printk.h>
#include <zephyr/sys/byteorder.h>
#include <zephyr/kernel.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/sensor.h>

#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/hci.h>
#include <zephyr/bluetooth/conn.h>
#include <zephyr/bluetooth/gatt.h>
#include <bluetooth/services/lbs.h>      

#define DEVICE_NAME             CONFIG_BT_DEVICE_NAME

static struct bt_data ad[3];    // Advertising data array

static const struct bt_data sd[] = {
    BT_DATA_BYTES(BT_DATA_UUID128_ALL, BT_UUID_LBS_VAL),
};

int16_t temp_value = 0;     // 16-bit signed integer for temperature * 100
 
struct sensor_value temp_val;   // Zephyr sensor API structure to receive raw TMP112 output (int part and fraction part)
const struct device *temp_dev;  // Device pointer for the TMP112 sensor

// Bluetooth advertising parameters:
static const struct bt_le_adv_param adv_param = {
    .options = BT_LE_ADV_OPT_CONN,
    .interval_min = BT_GAP_ADV_FAST_INT_MIN_1,
    .interval_max = BT_GAP_ADV_FAST_INT_MAX_1,
};

void build_advertisement(void)
{
    static uint8_t mfg_data[4];

    mfg_data[0] = 0x59;          // Nordic Company ID LSB
    mfg_data[1] = 0x00;          // Nordic Company ID MSB
    mfg_data[2] = temp_value & 0xFF;
    mfg_data[3] = (temp_value >> 8) & 0xFF;

    ad[0] = (struct bt_data)BT_DATA_BYTES(BT_DATA_FLAGS, (BT_LE_AD_GENERAL | BT_LE_AD_NO_BREDR));
    ad[1] = (struct bt_data)BT_DATA(BT_DATA_NAME_COMPLETE, DEVICE_NAME, sizeof(DEVICE_NAME) - 1);
    ad[2] = (struct bt_data)BT_DATA(BT_DATA_MANUFACTURER_DATA, mfg_data, sizeof(mfg_data));
}

int main(void)
{
    int err;

    temp_dev = device_get_binding("TMP112");
    k_sleep(K_MSEC(100));  // Wait 100ms to allow sensor startup

    if (!temp_dev) {
        printk("TMP112 not found!\n");
        return 0;
    }

    if (sensor_sample_fetch(temp_dev) == 0 &&
        sensor_channel_get(temp_dev, SENSOR_CHAN_AMBIENT_TEMP, &temp_val) == 0) {
        float temperature = sensor_value_to_double(&temp_val);
        temp_value = (int16_t)roundf(temperature * 100.0f);
        printk("Temperature read: %d\n", temp_value);
    } else {
        printk("Sensor fetch failed\n");
        return 0;
    }

    build_advertisement();

    err = bt_enable(NULL);
    if (err) {
        printk("Bluetooth init failed (err %d)\n", err);
        return 0;
    }

    err = bt_le_adv_start(&adv_param, ad, ARRAY_SIZE(ad), sd, ARRAY_SIZE(sd));
    if (err) {
        printk("Advertising start failed (err %d)\n", err);
        return 0;
    }

    printk("Advertising started with temp value\n");

    while (1) {
        k_sleep(K_FOREVER);
    }
}
