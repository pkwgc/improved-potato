package com.ct.client;

import android.content.Context;
import android.util.Log;
import android.widget.Toast;

import com.tencent.mm.opensdk.modelpay.PayReq;
import com.tencent.mm.opensdk.openapi.IWXAPI;
import com.tencent.mm.opensdk.openapi.WXAPIFactory;

public class PaymentHandler {
    private static final String TAG = "PaymentHandler";

    public static boolean processPayment(Context context, PaymentParams params) {
        if (params == null || !params.isValid()) {
            Log.e(TAG, "Invalid payment parameters");
            Toast.makeText(context, "支付参数无效", Toast.LENGTH_SHORT).show();
            return false;
        }

        try {
            IWXAPI api = WXAPIFactory.createWXAPI(context, params.appId, true);
            api.registerApp(params.appId);

            if (!api.isWXAppInstalled()) {
                Log.e(TAG, "WeChat is not installed");
                Toast.makeText(context, "请先安装微信客户端", Toast.LENGTH_SHORT).show();
                return false;
            }


            PayReq request = new PayReq();
            request.appId = params.appId;
            request.partnerId = params.partnerId;
            request.prepayId = params.prepayId;
            request.packageValue = params.spreadField != null ? params.spreadField : "Sign=WXPay";
            request.nonceStr = params.nonceStr;
            request.timeStamp = params.timestamp;
            request.sign = params.sign;

            Log.d(TAG, "Sending payment request: " + params.toString());

            boolean result = api.sendReq(request);
            
            if (result) {
                Log.d(TAG, "Payment request sent successfully");
                Toast.makeText(context, "正在启动微信支付...", Toast.LENGTH_SHORT).show();
            } else {
                Log.e(TAG, "Failed to send payment request");
                Toast.makeText(context, "启动微信支付失败", Toast.LENGTH_SHORT).show();
            }

            return result;

        } catch (Exception e) {
            Log.e(TAG, "Error processing payment", e);
            Toast.makeText(context, "支付处理异常: " + e.getMessage(), Toast.LENGTH_SHORT).show();
            return false;
        }
    }

    public static void handlePaymentResult(int errorCode, String errorMsg) {
        Log.d(TAG, "Payment result - Code: " + errorCode + ", Message: " + errorMsg);
        
        switch (errorCode) {
            case 0: // Success
                Log.i(TAG, "Payment successful");
                break;
            case -1: // Error
                Log.e(TAG, "Payment failed: " + errorMsg);
                break;
            case -2: // User cancelled
                Log.w(TAG, "Payment cancelled by user");
                break;
            default:
                Log.w(TAG, "Unknown payment result: " + errorCode);
                break;
        }
    }
}
