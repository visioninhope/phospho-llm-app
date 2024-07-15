import { DatePickerWithRange } from "@/components/date-range";
import FilterComponent from "@/components/filters";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { toast } from "@/components/ui/use-toast";
import { dataStateStore } from "@/store/store";
import { navigationStateStore } from "@/store/store";
import { useUser } from "@propelauth/nextjs/client";
import { Separator } from "@radix-ui/react-dropdown-menu";
import { ChevronRight } from "lucide-react";
import React from "react";
import { useState } from "react";

const CreateDataset = () => {
  const { accessToken } = useUser();
  const project_id = navigationStateStore((state) => state.project_id);
  const orgMetadata = dataStateStore((state) => state.selectedOrgMetadata);
  const dataFilters = navigationStateStore((state) => state.dataFilters);
  const [isCreatingDataset, setIsCreatingDataset] = useState(false);
  // Params for the dataset creation
  const [limit, setLimit] = useState(400); // Limit on the dataset size
  const [useSmartSampling, setUseSmartSampling] = useState(false); // To know wich sampling_type send to the backend

  // Hardcoded limit for the dataset size
  const MAX_LIMIT = 2000;

  if (!project_id) {
    return <></>;
  }

  // We create a function to generate a dataset name that is nice for humans
  // TODO: add some easter eggs
  const colors = [
    "green",
    "neon",
    "crimson",
    "azure",
    "emerald",
    "sapphire",
    "amber",
    "violet",
    "coral",
    "indigo",
    "teal",
    "scarlet",
    "jade",
    "slate",
    "ivory",
  ];

  const fruits = [
    "mango",
    "kiwi",
    "pineapple",
    "dragonfruit",
    "papaya",
    "lychee",
    "pomegranate",
    "guava",
    "fig",
    "passionfruit",
    "starfruit",
    "coconut",
    "jackfruit",
  ];

  function getRandomItem<T>(array: T[]): T {
    return array[Math.floor(Math.random() * array.length)];
  }

  function getCompactDate() {
    const date = new Date();
    const year = date.getFullYear().toString().slice(-2);
    const month = (date.getMonth() + 1).toString().padStart(2, "0");
    const day = date.getDate().toString().padStart(2, "0");
    return `${year}${month}${day}`;
  }

  function generateDatasetName() {
    const color = getRandomItem(colors);
    const fruit = getRandomItem(fruits);
    const date = getCompactDate();
    return `${color}-${fruit}-${date}`;
  }

  const [datasetName, setDatasetName] = useState(generateDatasetName());

  async function createNewDataset() {
    // Disable the button while we are creating the dataset
    setIsCreatingDataset(true);
    console.log(useSmartSampling);
    try {
      await fetch(`/api/datasets`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer " + accessToken,
        },
        body: JSON.stringify({
          project_id: project_id,
          limit: limit,
          workspace_id: orgMetadata?.argilla_workspace_id,
          dataset_name: datasetName,
          filters: dataFilters,
          sampling_parameters: {
            sampling_type: useSmartSampling ? "balanced" : "naive",
          },
        }),
      }).then((response) => {
        if (response.status == 200) {
          toast({
            title: "Dataset created",
            description: "View it in your Argilla platform",
          });
        } else if (response.status == 400) {
          response.json().then((data) => {
            toast({
              title: "Could not create dataset",
              description: data.detail,
            });
          });
        } else {
          toast({
            title: "Could not create dataset",
            description: response.text(),
          });
        }
        setIsCreatingDataset(false);
      });
    } catch (e) {
      toast({
        title: "Error when creating dataset",
        description: JSON.stringify(e),
      });
      setIsCreatingDataset(false);
    }
  }

  const handleSmartSamplingChange = (checked: boolean) => {
    setUseSmartSampling(checked === true);
  };

  return (
    <Sheet>
      <SheetTrigger>
        <Button className="default">
          Export a new dataset
          <ChevronRight className="w-4 h-4 ml-2" />
        </Button>
      </SheetTrigger>
      <SheetContent className="md:w-1/2 overflow-auto">
        <SheetTitle>Export data</SheetTitle>
        <SheetDescription>
          Export datasets from your project for labelling in your Argilla
          platform.
        </SheetDescription>
        <Separator className="my-8" />
        <div className="flex flex-wrap mt-4">
          <DatePickerWithRange className="mr-2" />
          <FilterComponent variant="tasks" />
        </div>
        {/* <div className="items-top flex space-x-2 mt-4">
                    <Checkbox
                        id="terms1"
                        checked={useSmartSampling}
                        onCheckedChange={handleSmartSamplingChange}
                    />
                    <div className="grid gap-1.5 leading-none">
                        <label
                            htmlFor="terms1"
                            className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                        >
                            Force balanced dataset
                        </label>
                    </div>
                </div> */}
        <div className="mt-4">
          <label
            htmlFor="limit"
            className="block text-sm font-medium text-gray-700"
          >
            Dataset size (max {MAX_LIMIT} rows)
          </label>
          <Input
            type="number"
            name="limit"
            id="limit"
            value={limit}
            onChange={(e) =>
              setLimit(Math.min(Number(e.target.value), MAX_LIMIT))
            }
            className="mt-1 block w-full"
            placeholder="100"
            min={1}
            max={MAX_LIMIT}
          />
        </div>
        <div className="mt-4">
          <label
            htmlFor="datasetName"
            className="block text-sm font-medium text-gray-700"
          >
            Dataset Name
          </label>
          <Input
            type="text"
            name="datasetName"
            id="datasetName"
            value={datasetName}
            onChange={(e) => setDatasetName(e.target.value)}
            className="mt-1 block w-full"
            placeholder="your-dataset-name"
          />
        </div>
        <div className="flex justify-end mt-4">
          <Button
            type="submit"
            onClick={createNewDataset}
            disabled={isCreatingDataset}
          >
            Create dataset
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
};

export default CreateDataset;
