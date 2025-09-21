package com.wechat.payment.wxapi;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.util.Log;
import android.widget.Toast;

import com.tencent.mm.opensdk.constants.ConstantsAPI;
import com.tencent.mm.opensdk.modelbase.BaseReq;
import com.tencent.mm.opensdk.modelbase.BaseResp;
import com.tencent.mm.opensdk.modelpay.PayResp;
import com.tencent.mm.opensdk.openapi.IWXAPI;
import com.tencent.mm.opensdk.openapi.IWXAPIEventHandler;
import com.tencent.mm.opensdk.openapi.WXAPIFactory;
import com.wechat.payment.PaymentHandler;

public class WXPayEntryActivity extends Activity implements IWXAPIEventHandler {
    private static final String TAG = "WXPayEntryActivity";
    
    private IWXAPI api;

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        api = WXAPIFactory.createWXAPI(this, null);
        api.handleIntent(getIntent(), this);
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        api.handleIntent(intent, this);
    }

    @Override
    public void onReq(BaseReq req) {
        Log.d(TAG, "onReq: " + req.getType());
    }

    @Override
    public void onResp(BaseResp resp) {
        Log.d(TAG, "onResp: " + resp.errCode);
        
        if (resp.getType() == ConstantsAPI.COMMAND_PAY_BY_WX) {
            PayResp payResp = (PayResp) resp;
            handlePaymentResponse(payResp);
        }
        
        finish();
    }

    private void handlePaymentResponse(PayResp resp) {
        String message;
        String resultMessage = "";
        
        switch (resp.errCode) {
            case 0: // Success
                message = "支付成功";
                resultMessage = "Payment successful";
                Log.i(TAG, "Payment successful");
                break;
            case -1: // Error
                message = "支付失败";
                resultMessage = "Payment failed: " + resp.errStr;
                Log.e(TAG, "Payment failed: " + resp.errStr);
                break;
            case -2: // User cancelled
                message = "支付已取消";
                resultMessage = "Payment cancelled by user";
                Log.w(TAG, "Payment cancelled by user");
                break;
            default:
                message = "支付结果未知";
                resultMessage = "Unknown payment result: " + resp.errCode;
                Log.w(TAG, "Unknown payment result: " + resp.errCode);
                break;
        }

        Toast.makeText(this, message, Toast.LENGTH_SHORT).show();
        PaymentHandler.handlePaymentResult(resp.errCode, resp.errStr);
        
        sendResultToH5(resp.errCode, resultMessage);
    }

    private void sendResultToH5(int errorCode, String message) {
        try {
            String resultScheme = "wechatpay://result?code=" + errorCode + "&message=" + 
                                 java.net.URLEncoder.encode(message, "UTF-8");
            
            Intent intent = new Intent(Intent.ACTION_VIEW);
            intent.setData(android.net.Uri.parse(resultScheme));
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            
            try {
                startActivity(intent);
                Log.d(TAG, "Result sent to H5: " + resultScheme);
            } catch (Exception e) {
                Log.w(TAG, "Could not send result to H5", e);
            }
            
        } catch (Exception e) {
            Log.e(TAG, "Error sending result to H5", e);
        }
    }
}
