import torch
import torch.nn as nn
import torch.nn.functional as F
from pytorch_pretrained_bert import BertModel

from tools.accuracy_tool import single_label_top1_accuracy

def conv3x3(in_planes, out_planes, stride=1):#基本的3x3卷积
    """3x3 convolution with padding"""
    return nn.Conv2d(in_planes, out_planes, kernel_size=3, stride=stride,
                     padding=1, bias=False)

class BertQACNN(nn.Module):
    def __init__(self, config, gpu_list, *args, **params):
        super(BertQACNN, self).__init__()

        self.bert = BertModel.from_pretrained(config.get("model", "bert_path"))
        # print(self.bert)
        # self.rank_module = nn.Linear(768 * config.getint("data", "topk"), 1)
        # self.singlerank_module = nn.Linear(262144, 4)
        self.criterion = nn.CrossEntropyLoss()

        # self.multi = config.getboolean("data", "multi_choice")
        # self.multirank_module = nn.Linear(262144, 11)
        self.accuracy_function = single_label_top1_accuracy

        # 12, 256, 256

        p = 32
        p2 = 64

        self.conv1 = nn.Conv2d(12, p, kernel_size=11, stride=1, padding=5, bias=False)
        self.conv2 = nn.Conv2d(p, p2, kernel_size=5, stride=1, padding=2, bias=False)

        self.conv3 = nn.Conv2d(p2, p2, kernel_size=3, stride=1, padding=1, bias=False)
        self.conv4 = nn.Conv2d(p2, p2, kernel_size=3, stride=1, padding=1, bias=False)
        self.conv5 = nn.Conv2d(p2, p2, kernel_size=3, stride=1, padding=1, bias=False)
        self.conv6 = nn.Conv2d(p2, p2, kernel_size=3, stride=1, padding=1, bias=False)

        self.conv7 = nn.Conv2d(p2, p, kernel_size=3, stride=1, padding=1, bias=False)
        self.conv8 = nn.Conv2d(p, p, kernel_size=3, stride=1, padding=1, bias=False)

        self.conv9 = nn.Conv2d(p, p, kernel_size=3, stride=1, padding=1, bias=False)
        self.conv10 = nn.Conv2d(p, 4, kernel_size=3, stride=1, padding=1, bias=False)

        self.maxpool1 = nn.MaxPool2d(kernel_size=5, stride=1, padding=2)
        self.maxpool2 = nn.MaxPool2d(kernel_size=3, stride=1, padding=1)
        self.maxpool3 = nn.MaxPool2d(kernel_size=3, stride=1, padding=1)
        self.maxpool4 = nn.MaxPool2d(kernel_size=3, stride=1, padding=1)

        self.relu = nn.ReLU(inplace=True)
        self.relu1 = nn.ReLU(inplace=True)
        self.relu2 = nn.ReLU(inplace=True)
        self.relu3 = nn.ReLU(inplace=True)
        self.relu4 = nn.ReLU(inplace=True)
        self.relu5 = nn.ReLU(inplace=True)
        self.relu6 = nn.ReLU(inplace=True)
        self.relu7 = nn.ReLU(inplace=True)
        self.relu8 = nn.ReLU(inplace=True)

        self.bn1 = nn.BatchNorm2d(p2)
        self.bn2 = nn.BatchNorm2d(p2)
        self.bn3 = nn.BatchNorm2d(p)

        self.rank_module1 = nn.Linear(262144, 15)
        # self.rank_module3 = nn.Linear(600, 4)
        # self.rank_module3m = nn.Linear(600, 11)


    def init_multi_gpu(self, device, config, *args, **params):
        self.bert = nn.DataParallel(self.bert, device_ids=device)

    # precision: 0.27135616269007296
    # precision: 0.22066748605464687
    # precision: 0.24263366548805315
    def forward(self, data, config, gpu_list, acc_result, mode):
        text = data["text"]
        token = data["token"]
        mask = data["mask"]

        batch = text.size()[0]
        option = text.size()[1]
        k = config.getint("data", "topk")
        option = option // k


        text = text.view(text.size()[0] * text.size()[1], text.size()[2])
        token = token.view(token.size()[0] * token.size()[1], token.size()[2])
        mask = mask.view(mask.size()[0] * mask.size()[1], mask.size()[2])

        encode, y = self.bert.forward(text, token, mask, output_all_encoded_layers=False)
        l = encode.size()[1] #256
        p = encode.size()[2]
        # y = y.view(batch  * option, l, -1)
        # #y = self.rank_module(y)
        encode = encode.view(batch, 3*option, l, p//3)

        y = self.conv1(encode)
        y = self.relu(y)
        y = self.conv2(y)
        y = self.relu1(y)
        y = self.maxpool1(y)
        y = self.bn1(y)

        y = self.conv3(y)
        y = self.relu2(y)
        y = self.conv5(y)
        y = self.relu3(y)
        y = self.conv6(y)
        y = self.relu4(y)
        y = self.maxpool2(y)
        y = self.bn2(y)

        y = self.conv7(y)
        y = self.relu5(y)
        y = self.conv8(y)
        y = self.relu6(y)
        y = self.maxpool3(y)
        y = self.bn3(y)

        y = self.conv9(y)
        y = self.relu7(y)
        y = self.conv10(y)
        y = self.relu8(y)
        y = self.maxpool4(y)

        y = y.view(batch, -1)

        y = self.rank_module1(y)

        label = data["label"]
        loss = self.criterion(y, label)
        acc_result = self.accuracy_function(y, label, config, acc_result)

        answer = []
        predm = y.argmax(dim=1)
        preds = y[:, 0:3].argmax(dim=1)
        for x in range(batch):
            if data['sorm'][x]:
                i = predm[x]
                subanswer = []
                if i == 0:
                    subanswer.append('A')
                if i == 1:
                    subanswer.append('B')
                if i == 2:
                    subanswer.append('C')
                if i == 3:
                    subanswer.append('D')
                if i == 4:
                    subanswer = ['A', 'B']
                if i == 5:
                    subanswer = ['A', 'C']
                if i == 6:
                    subanswer = ['B', 'C']
                if i == 7:
                    subanswer = ['A', 'B', 'C']
                if i == 8:
                    subanswer = ['A', 'D']
                if i == 9:
                    subanswer = ['B', 'D']
                if i == 10:
                    subanswer = ['A', 'B', 'D']
                if i == 11:
                    subanswer = ['C', 'D']
                if i == 12:
                    subanswer = ['A', 'C', 'D']
                if i == 13:
                    subanswer = ['B', 'C', 'D']
                if i == 14:
                    subanswer = ['A', 'B', 'C', 'D']
                answer.append(subanswer)
            else:
                answer.append(chr(ord('A') + preds[x]))

        output = [{"id": id, "answer": [answer]} for id, answer in zip(data['id'], answer)]
        return {"loss": loss, "acc_result": acc_result, "output": output}
