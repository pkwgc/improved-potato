package com.ct.client;

import android.os.Parcel;
import android.os.Parcelable;

public class PaymentParams implements Parcelable {
    public String prepayId;
    public String appId;
    public String partnerId;
    public String nonceStr;
    public String sign;
    public String spreadField;
    public String timestamp;

    public PaymentParams() {
    }

    public PaymentParams(String prepayId, String appId, String partnerId, 
                        String nonceStr, String sign, String spreadField, String timestamp) {
        this.prepayId = prepayId;
        this.appId = appId;
        this.partnerId = partnerId;
        this.nonceStr = nonceStr;
        this.sign = sign;
        this.spreadField = spreadField;
        this.timestamp = timestamp;
    }

    protected PaymentParams(Parcel in) {
        prepayId = in.readString();
        appId = in.readString();
        partnerId = in.readString();
        nonceStr = in.readString();
        sign = in.readString();
        spreadField = in.readString();
        timestamp = in.readString();
    }

    public static final Creator<PaymentParams> CREATOR = new Creator<PaymentParams>() {
        @Override
        public PaymentParams createFromParcel(Parcel in) {
            return new PaymentParams(in);
        }

        @Override
        public PaymentParams[] newArray(int size) {
            return new PaymentParams[size];
        }
    };

    @Override
    public int describeContents() {
        return 0;
    }

    @Override
    public void writeToParcel(Parcel dest, int flags) {
        dest.writeString(prepayId);
        dest.writeString(appId);
        dest.writeString(partnerId);
        dest.writeString(nonceStr);
        dest.writeString(sign);
        dest.writeString(spreadField);
        dest.writeString(timestamp);
    }

    public boolean isValid() {
        return prepayId != null && !prepayId.isEmpty() &&
               appId != null && !appId.isEmpty() &&
               partnerId != null && !partnerId.isEmpty() &&
               nonceStr != null && !nonceStr.isEmpty() &&
               sign != null && !sign.isEmpty() &&
               timestamp != null && !timestamp.isEmpty();
    }

    @Override
    public String toString() {
        return "PaymentParams{" +
                "prepayId='" + prepayId + '\'' +
                ", appId='" + appId + '\'' +
                ", partnerId='" + partnerId + '\'' +
                ", nonceStr='" + nonceStr + '\'' +
                ", sign='" + sign + '\'' +
                ", spreadField='" + spreadField + '\'' +
                ", timestamp='" + timestamp + '\'' +
                '}';
    }
}
